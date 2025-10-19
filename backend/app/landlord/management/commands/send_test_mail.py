from django.core.mail import send_mail
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Send a test email to verify SMTP delivery (Mailhog in dev)."

    def add_arguments(self, parser):
        parser.add_argument("to_email", type=str)

    def handle(self, *args, **options):
        to_email = options["to_email"]
        sent = send_mail(
            subject="UVM Test Mail",
            message="This is a test email from UVM.",
            from_email=None,
            recipient_list=[to_email],
            fail_silently=False,
        )
        self.stdout.write(self.style.SUCCESS(f"Sent {sent} test email(s) to {to_email}"))
