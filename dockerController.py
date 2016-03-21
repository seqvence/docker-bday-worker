import json
import logging

import requests
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import app_config as config
from docker import Client, errors

status = ["Downloading", "Image missing", "Configuring image",
          "Running image", "Testing endpoint", "Failed", "Successful"]

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.INFO)


class ContainerError(Exception):
    pass

class DockerError(Exception):
    pass


class DockerController:
    def __init__(self, docker_endpoint, docker_network):
        if not docker_endpoint:
            raise DockerError('No docker endpoint available.')
        self.cli = Client(docker_endpoint)
        self.network = docker_network
        self.retries = Retry(total=5,
                             backoff_factor=1,
                             status_forcelist=[500, 502, 503, 504])

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
            download_log = list(self.cli.pull(image_name, stream=True, insecure_registry=False))
            # Extracting the last line from the output
            # Possible outcome:
            # Status: Downloaded newer image for pierrezemb/gostatic
            # Status: Image is up to date for pierrezemb/gostatic
            # Error: Tag
            try:
                logging.info("Image {} downloaded successfully".format(image_name))
                logging.info(json.loads(download_log[-1])['status'])
                return True
            except Exception, e:
                logging.error("Failed to download image {}".format(image_name))
                logging.error(json.loads(download_log[-1])['error'])
                return False
        else:
            logging.info("Image {} not found.".format(image_name))
            return False

    def test_endpoint(self, ip, port, path):
        """
        Connect to an endpoint using http
        :param ip: string
        :param port: string
        :return: boolean
        """
        logging.info('Testing endpoint {}:{}{}'.format(ip, port, path))
        s = requests.Session()
        s.mount('http://', HTTPAdapter(max_retries=self.retries))
        try:
            r = s.get('http://{}:{}{}'.format(ip, port, path))
        except requests.exceptions.Timeout:
            logging.error('Timeout connecting to {}:{}{}'.format(ip, port, path))
            return False
        except requests.exceptions.ConnectionError:
            logging.error('Failed connecting to {}:{}{}'.format(ip, port, path))
            return False
        except Exception, e:
            logging.error(e)
            return False
        if r.status_code == 200 and r.text != config.container['default_message']:
            logging.info('{}:{}{} passed validation'.format(ip, port, path))
            return True
        else:
            logging.info('{}:{}{} failed validation'.format(ip, port, path))
            return False

    def run_container(self, image_name):
        """
        Run container and return its ID and IP Address
        :param image_name: string
        :return: string, string
        """
        logging.info("Connecting to Docker daemon")
        try:
            build_container = self.cli.create_container(image=image_name, ports=[80])
        except errors.APIError:
            raise ContainerError('Could not create container for image {}'.format(image_name))

        networks = self.cli.networks(names=[self.network])
        if not len(networks):
            raise DockerError('Could not find network {}'.format(self.network))

        self.cli.connect_container_to_network(container=build_container.get('Id'), net_id=networks[0]['Id'])
        self.cli.start(container=build_container.get('Id'))

        running_container = self.cli.inspect_container(container=build_container.get('Id'))

        if running_container['State']['Status'] != 'running':
            logging.error('Container {} died too soon.'.format(image_name))
            return

        if not running_container['NetworkSettings']['IPAddress']:
            logging.error('Container {} has no network. Something went wrong'.format(image_name))
            return

        return build_container.get('Id'), running_container['NetworkSettings']['Networks'][self.network]['IPAddress']

    def clean_container(self, container_id, image_name=None):
        """
        Stop and remove container, remove image
        :param running_container: dict
        :param image_name: string
        :return: None
        """
        logging.info('Time to do the clean up')
        logging.info('Stoping container {}'.format(image_name))
        self.cli.stop(container=container_id, timeout=20)
        logging.info('Removing container {}'.format(image_name))
        self.cli.remove_container(container=container_id)
        try:
            if image_name:
                logging.info("Removing image {}".format(image_name))
                self.cli.remove_image(image=image_name, force=True)
            return
        except Exception, e:
            logging.error("Image {} was missing when trying to remove. Possible concurrency problems".format(image_name))
            return


def main(image_name):
    client = DockerController("tcp://192.168.64.2:2375")
    if client.download_image(image_name):
        client.run_container(image_name)


if __name__ == '__main__':
    main("vstoican/results")
    pass
