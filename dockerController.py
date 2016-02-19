import json
import logging

import requests
from docker import Client

status = ["Downloading", "Image missing", "Configuring image",
          "Running image", "Testing endpoint", "Failed", "Successful"]

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.INFO)


class DockerController:
    def __init__(self, docker_endpoint):
        self.cli = Client(docker_endpoint)

    def download_image(self, image_name):
        """
        Download docker image submitted by participants
        :param image_name: string
        :return:
        """
        if ":" in image_name:
            image_repo, image_tag = image_name.split(":")
            logging.info("Search repo {} for image {}".format(image_repo, image_tag))
            results = self.cli.search(image_repo)
        else:
            results = self.cli.search(image_name)

        logging.info("Search returned {} result(s).".format(len(results)))

        if len(results) > 0:
            logging.info("Downloading image {}".format(image_name))
            action = self.cli.pull(image_name, stream=True, insecure_registry=False)

            # Extracting the last line from the output
            # Possible outcome:
            # Status: Downloaded newer image for pierrezemb/gostatic
            # Status: Image is up to date for pierrezemb/gostatic
            logging.info(json.loads(list(action)[-1])['status'])
            return True
        else:
            logging.warn("Image {} not found.".format(image_name))
            return False

    @staticmethod
    def test_endpoint(ip, port):
        logging.info('Testing endpoint {}:{}'.format(ip, port))
        try:
            r = requests.get('http://{}:{}'.format(ip, port), timeout=3)
        except requests.exceptions.Timeout:
            logging.error('Timeout connecting to {}:{}'.format(ip, port))
            return False
        except Exception, e:
            logging.error(e)
            return False
        if r.status_code == 200:
            logging.info('{}:{} passed validation'.format(ip, port))
            return True
        else:
            logging.info('{}:{} failed validation'.format(ip, port))
            return False

    def run_container(self, image_name):
        logging.info("Connecting to Docker daemon")
        container = self.cli.create_container(image=image_name, ports=[80])
        networks = self.cli.networks(names=['compose_default'])
        self.cli.connect_container_to_network(container=container.get('Id'), net_id=networks[0]['Id'])
        self.cli.start(container=container.get('Id'))
        container = self.cli.inspect_container(container=container.get('Id'))
        if container['State']['Status'] != 'running':
            logging.error('Container {} died too soon.'.format(image_name))
            return
        if not container['NetworkSettings']['IPAddress']:
            logging.error('Container {} has no network. Something went wrong'.format(image_name))
            return
        test_result = self.test_endpoint(container['NetworkSettings']['Networks']['compose_default']['IPAddress'], 80)
        logging.info('Stoping container {}'.format(image_name))
        self.cli.stop(container=container.get('Id'), timeout=20)
        logging.info('Removing container {}'.format(image_name))
        self.cli.remove_container(container=container.get('Id'))
        logging.info("Removing image {}".format(image_name))
        self.cli.remove_image(image=image_name, force=True)
        return test_result


def main(image_name):
    client = DockerController("tcp://192.168.64.2:2375")
    client.run_container(image_name)
    if client.download_image(image_name):
        client.run_container(image_name)


if __name__ == '__main__':
    # main("appcontainers/apache:ubuntu_14.04")
    # main("pierrezemb/gostatic")
    pass
