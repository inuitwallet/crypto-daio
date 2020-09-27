from daio.celery import app


@app.task
def repair_transactions():
    pass
