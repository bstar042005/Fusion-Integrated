from django.db import transaction
from django.utils import timezone
from .models import LeaveBalance, LeaveRequest
from datetime import timedelta

def apply_leave(user_id, leave_type_id, start_date_str, end_date_str, reason=None):
    """
    Initiates a new leave request.
    
    Args:
        user_id (int): ID of the employee applying for leave.
        leave_type_id (int): ID of the leave type (e.g., Sick, Annual).
        start_date_str (str): Start date in 'YYYY-MM-DD' format.
        end_date_str (str): End date in 'YYYY-MM-DD' format.
        reason (str, optional): Brief reason for the leave.

    Returns:
        dict: A dictionary containing either the created request ID or an error message.
    """
    try:
        from django.utils.dateparse import parse_date
        
        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str)
        
        if not start_date or not end_date:
            return {"error": "Invalid date format provided."}

        request = LeaveRequest.objects.create(
            user_id=user_id,
            leave_type_id=leave_type_id,
            start_date=start_date,
            end_date=end_date,
            reason=reason or "",
            status='PENDING'
        )
        
        return {"id": request.id, "status": "submitted", "message": "Leave request submitted successfully."}
    
    except Exception as e:
        return {"error": f"Failed to create leave request: {str(e)}"}

def process_leave_approval(request_id, approver_user=None):
    """
    Processes the approval of a leave request and deducts the balance.
    
    Args:
        request_id (int): ID of the leave request to approve.
        approver_user (User instance, optional): The user performing the approval 
                                                 (used for logging). Defaults to None.

    Returns:
        dict: A dictionary containing either success status/deduction info or error details.
    """
    try:
        request = LeaveRequest.objects.get(id=request_id)
        
        if request.status != 'PENDING':
            return {"error": f"This request cannot be approved (Current Status: {request.status})."}

        days_to_deduct = (request.end_date - request.start_date).days + 1
        leave_type_name = request.leave_type.name
        
        with transaction.atomic():
            # Retrieve and update balance
            balance_record, created = LeaveBalance.objects.get_or_create(
                user=request.user,
                leave_type=request.leave_type
            )
            
            if not created:
                old_balance = balance_record.current_balance
                new_balance = old_balance - days_to_deduct
                
                # Optional: Prevent negative balances? 
                # If logic requires blocking requests with insufficient balance before save:
                # if new_balance < 0: raise ValidationError("Insufficient leave balance.")

                balance_record.current_balance = new_balance
                balance_record.save(update_fields=['current_balance'])
            
            # Update request status
            request.status = 'APPROVED'
            request.approved_by = approver_user if approver_user else None
            # request.approval_date = timezone.now() # If you want to store exact approval time
            
            request.save(update_fields=['status', 'approved_by', 'approval_date'])

        return {
            "status": "success",
            "request_id": request_id,
            "message": f"Leave request approved. {leave_type_name} balance deducted.",
            "previous_balance": old_balance if not created else None, 
            "current_balance": balance_record.current_balance
        }

    except LeaveRequest.DoesNotExist:
        return {"error": "Leave request not found."}
    except ValueError:
        return {"error": "Invalid dates in the leave request configuration."}
    except Exception as e:
        return {"error": f"Error processing approval: {str(e)}"}

def process_leave_rejection(request_id, reason=None):
    """
    Rejects a pending leave request.
    
    Args:
        request_id (int): ID of the leave request to reject.
        reason (str, optional): Reason for rejection (stored or logged).

    Returns:
        dict: Success or error message.
    """
    try:
        request = LeaveRequest.objects.get(id=request_id)
        
        if request.status != 'PENDING':
            return {"error": f"This request cannot be rejected (Current Status: {request.status})."}

        request.status = 'REJECTED'
        # Optionally store reason if the model field exists and is writable here
        # request.rejection_reason = reason 
        
        request.save(update_fields=['status']) # Add rejection_reason to fields if implemented in model

        return {
            "status": "success",
            "request_id": request_id,
            "message": f"Leave request rejected.",
            "reason": reason or ""
        }

    except LeaveRequest.DoesNotExist:
        return {"error": "Leave request not found."}
    except Exception as e:
        return {"error": f"Error processing rejection: {str(e)}"}