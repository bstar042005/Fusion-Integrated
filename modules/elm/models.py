from django.db import models
from django.conf import settings

class LeaveType(models.Model):
    TYPE_CHOICES = [
        ('S', 'Sick'),
        ('P', 'Personal'),
        ('A', 'Annual'),
        ('U', 'Unpaid'),
    ]
    
    name = models.CharField(max_length=50, unique=True)
    type_code = models.CharField(max_length=1, choices=TYPE_CHOICES)
    default_balance = models.IntegerField(default=24) # 30 days default

    class Meta:
        verbose_name_plural = "Leave Types"

    def __str__(self):
        return f"{self.name} ({self.get_type_code_display()})"

class LeaveBalance(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='balances')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name='balances')
    current_balance = models.IntegerField(default=0)

    class Meta:
        unique_together = ['user', 'leave_type']
        verbose_name_plural = "Leave Balances"

    def __str__(self):
        return f"{self.user.username} - {self.leave_type.name}"

class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name='requests')
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approvals')
    approval_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.start_date} to {self.end_date}"