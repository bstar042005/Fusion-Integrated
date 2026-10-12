from rest_framework import serializers
from .models import LeaveType, LeaveBalance, LeaveRequest

class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ['id', 'name', 'type_code', 'default_balance']

class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_display = serializers.CharField(source='leave_type.name', read_only=True)
    
    class Meta:
        model = LeaveBalance
        fields = ['user', 'leave_type', 'leave_type_display', 'current_balance']
        # Read-only for typical API usage unless admin is handling it

class LeaveRequestSerializer(serializers.ModelSerializer):
    leave_type_display = serializers.CharField(source='leave_type.name', read_only=True)
    user_display = serializers.ReadOnlyField(source='user.username')
    
    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'user', 'user_display', 'leave_type', 'leave_type_display', 
            'start_date', 'end_date', 'reason', 'status', 'approved_by'
        ]
        read_only_fields = ['user', 'status', 'approved_by', 'approval_date']

    def validate(self, data):
        user = self.instance.user if self.instance else self.context['request'].user
        balance_obj = LeaveBalance.objects.filter(user=user, leave_type=data.get('leave_type')).first()
        
        if not balance_obj:
            raise serializers.ValidationError("No active balance record found for this leave type.")
            
        days_requested = (data['end_date'] - data['start_date']).days + 1
        
        if balance_obj.current_balance < days_requested:
            raise serializers.ValidationError(f"Insufficient balance. You have {balance_obj.current_balance} {self.instance.leave_type.name} leave(s) remaining.")
            
        # Basic overlap check could be added here if required by business logic
        
        return data