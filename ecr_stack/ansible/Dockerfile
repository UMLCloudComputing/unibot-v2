FROM python:3.13-slim-bookworm
COPY . .
RUN pip install --upgrade pip && pip install ansible
ENTRYPOINT ["ansible-playbook", "-i", "inventory", "download-vectorize-playbook.yaml"]
