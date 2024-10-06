FROM public.ecr.aws/lambda/python:3.10

COPY handler.py ${LAMBDA_TASK_ROOT}
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt --target "${LAMBDA_TASK_ROOT}" \
    && rm -rf /root/.cache/pip

CMD ["handler.lambda_handler"]
