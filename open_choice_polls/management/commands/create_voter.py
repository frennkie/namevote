from django.core.management.base import BaseCommand
from open_choice_polls.models import Voter


class Command(BaseCommand):
    help = 'Create some voters'

    def add_arguments(self, parser):
        parser.add_argument('--amount', type=int, default=1, help='Amount to create')
        parser.add_argument('--question', type=str, help='ID of Question to assign')

    def handle(self, *args, **options):
        amount = options.get('amount')
        question = options.get('question')

        if question:
            res = Voter.create_voter(amount, code_valid_timedelta_days=30, question_id=question)
        else:
            res = Voter.create_voter(amount, code_valid_timedelta_days=30)

        if res:
            self.stdout.write(self.style.SUCCESS('Successfully created {} voter(s)'.format(amount)))
            for voter in res:
                self.stdout.write(self.style.SUCCESS('Voter: {}'.format(voter.username)))
        else:
            self.stdout.write(self.style.WARNING('Failed to create {} voter(s)'.format(amount)))
