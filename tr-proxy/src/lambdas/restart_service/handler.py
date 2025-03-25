import os
from time import sleep
from types import SimpleNamespace

import boto3
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

client = boto3.client('ecs')

def lambda_handler(event, context):
    logger.info(event)

    cluster = event.get("CLUSTER_NAME", "SpecDev")
    service_name = event.get("SERVICE_NAME", "TrProxy")

    logger.info(f"Starting restart of {service_name} in {cluster} cluster")

    tasks = SimpleNamespace(**client.list_tasks(cluster=cluster, service_nam=service_name))

    has_running_tasks = False
    if "taskArns" in dir(tasks):
        for task in tasks.taskArns:
            logger.info(f"Rebooting task : {task} in {cluster}, {service_name}")
            client.stop_task(cluster=cluster, task=task, reason="reboot at scheduled time")

            while has_running_tasks is False:
                sleep(2)
                services = client.describe_services(cluster=cluster, services=[service_name])

                for item in services.get("services"):
                    service = SimpleNamespace(**item)
                    if service.serviceName == service_name:
                        has_running_tasks = service.runningCount > 0

                logger.info(f"Has running tasks: {has_running_tasks}")
            logger.info(f"All Tasks have been rebooted")
    else:
        logger.warning(f"No Tasks to reboot in {cluster}, {service_name}")


if __name__ == "__main__":
    lambda_handler(None, None)