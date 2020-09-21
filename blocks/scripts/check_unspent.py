import django

from blocks.models import TxOutput

django.setup()


def main():
    for output in TxOutput.objects.all():
        print("updating output {}".format(output))
        output.is_unspent = output.unspent
        output.save()


if __name__ == "__main__":
    main()
