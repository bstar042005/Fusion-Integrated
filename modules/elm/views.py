from rest_framework import viewsets, status, serializers as drf_serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import F
from datetime import timedelta
from .models import LeaveType, LeaveBalance, LeaveRequest
from .serializers import LeaveTypeSerializer, LeaveBalanceSerializer, LeaveRequestSerializer

class LeaveTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsAuthenticated]

class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LeaveBalance.objects.all()
    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return LeaveBalance.objects.filter(user=user)

class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return LeaveRequest.objects.filter(user=user)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def request_leave(self, request):
        serializer = LeaveRequestSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        instance = self.get_object()
        
        if not instance or instance.status != 'PENDING':
            return Response({"detail": "Cannot approve this request."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        
        # Simple authorization check (can be expanded)
        # if instance.approved_by and instance.approved_by != user:
        #     return Response({"detail": "Only the approver can approve this."}, status=403)

        # Check and deduct balance in a transaction-like manner (conceptually)
        try:
            days_to_deduct = (instance.end_date - instance.start_date).days + 1
            from django.db import transaction
            
            @transaction.atomic
            def perform_approve():
                balance_queryset = LeaveBalance.objects.filter(
                    user=instance.user, 
                    leave_type=instance.leave_type
                )
                
                if balance_queryset.exists():
                    balance_queryset.update(current_balance=F('current_balance') - days_to_deduct)
                
                instance.status = 'APPROVED'
                instance.approved_by = user
                # Simple date logic for approval record
                instance.approval_date = request.data.get('approval_date', instance.created_at if hasattr(instance, 'created_at') else None) 
                instance.save()
                
                return LeaveRequestSerializer(instance).data
                
            return Response({"status": "approved", **perform_approve()})
        except ValueError: # Handles date arithmetic errors
            return Response({"detail": "Invalid dates provided."}, status=status.HTTP_400_BAD_REQUEST)
            
    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def reject(self, request, pk=None):
        instance = self.get_object()
        
        if not instance or instance.status != 'PENDING':
            return Response({"detail": "Cannot reject this request."}, status=status.HTTP_400_BAD_REQUEST)

        instance.status = 'REJECTED'
        instance.approval_date = request.data.get('approval_date') # Optional reason field could be added
        instance.save()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)