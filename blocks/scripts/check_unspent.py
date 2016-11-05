import django
django.setup()

from blocks.models import TxOutput


def main():
    for output in TxOutput.objects.all():
        print("updating output {}".format(output))
        output.is_unspent = output.unspent
        output.save()

if __name__ == '__main__':
    main()
