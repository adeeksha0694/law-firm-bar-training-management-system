from django.db.models.signals import post_save
from django.apps import apps


def create_student_invoice(sender, instance, created, **kwargs):

    print("🔥 SIGNAL FUNCTION CALLED")

    if created:
        Invoice = apps.get_model('finance', 'Invoice')

        try:
            invoice = Invoice(
                invoice_type='student',
                student=instance,
                batch=instance.batch,
                amount=0
            )

            # bypass validation
            super(Invoice, invoice).save()

            print("✅ INVOICE CREATED")

        except Exception as e:
            print("❌ ERROR:", e)


def connect_signals():
    Student = apps.get_model('training', 'Student')
    post_save.connect(create_student_invoice, sender=Student)