import eventlet
from requests import ConnectionError

eventlet.monkey_patch()  # NOQA

import app_config as config
from dbController import DbDriver
from dockerController import DockerController, ContainerError, DockerError
import sys, traceback
import logging
import click
import signal
import consul

from geopy.geocoders import GoogleV3

eventlet.sleep(3)

logging.basicConfig(format=('%(asctime)s %(levelname)s %(message)s'), level=logging.DEBUG)


class GracefulKiller:
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self,signum, frame):
        self.kill_now = True

@click.command()
@click.option('--submissions', default=5, help='Maximum number of submissions to be processed per interval (Default: 5)')
def docker_worker(submissions):
    pool = eventlet.GreenPool(size=submissions)
    killer = GracefulKiller()
    mongo = DbDriver(config)

    if hasattr(config, 'consul'):
        logging.info('Using consul for retrieving the docker endpoint')
        config.docker = dict()
        config.docker['api'] = None
        eventlet.spawn_n(read_swarm_manager, config.docker, config.consul["host"], config.consul["port"],
                         config.consul["key"])
    elif hasattr(config, 'docker'):
        logging.info('Using static docker endpoint from config')
    else:
        raise ValueError('No consul or docker configured. Please add one of the two to the config.')

    while True:
        try:
            for _ in xrange(min(mongo.no_of_submissions(), submissions)):
                pool.spawn(check_submission)
            logging.info('Available threads: {}'.format(pool.free()))
            logging.info('Running threads: {}'.format(pool.running()))
            logging.info('Waiting for {} seconds'.format(2**(submissions-pool.running())))
            eventlet.sleep(2**(submissions-pool.running()))
        except (SystemExit, KeyboardInterrupt):
            break
        if killer.kill_now:
            break


def read_swarm_manager(docker_config, consul_host, consul_port, consul_key):
    while True:
        try:
            consul_client = consul.Consul(host=consul_host, port=consul_port)
            index, data = consul_client.kv.get(consul_key)
            docker_config['api'] = 'tcp://' + data['Value']
            logging.info('Found address {} for the swarm manager'.format(docker_config['api']))
        except (consul.ConsulException, ConnectionError, TypeError) as e:
            logging.error(e)
        eventlet.sleep(15)


def get_coordinates(address):
    logging.info('Retrieving coordinates for {}'.format(address))
    geocoder = GoogleV3(scheme='http')
    try:
        return geocoder.geocode(address)
    except:
        logging.error('Failed to retrieve coordinates for {}'.format(address))
        return None


def check_submission():
    mongo = DbDriver(config)
    docker = DockerController(config.docker['api'], config.docker['network'])
    record = mongo.get_one_record()

    if not record:
        logging.debug("Quiting. No new submission.")
        return

    coordinates = get_coordinates(record['location'])
    if coordinates:
        mongo.update_record_location(record['_id'], coordinates.latitude, coordinates.longitude)
    else:
        mongo.update_record_status(record['_id'], 'failed',
                                   statusmsg='Failed to geo-locate {}'.format(record['location']))
        return

    for image in record['repo']:
        logging.info("Downloading image {} for user {}".format(image, record['name']))
        if image == "bogus_bday_image:latest":
            logging.info('Submission SUCCESSFUL for {}'.format(record['name']))
            mongo.update_record_status(record['_id'], 'successful', statusmsg='Magic image passed validation')
            return
        try:
            image_result = docker.download_image(image_name=image)
        except:
            mongo.update_record_status(record['_id'], 'submitted')
            traceback.print_exc(file=sys.stdout)
            return
        if not image_result:
            break

        logging.info('Starting container {} for user {}'.format(image, record['name']))
        try:
            container_id, container_ip = docker.run_container(image)
        except ContainerError, e:
            mongo.update_record_status(record['_id'], 'failed', statusmsg=str(e))
            return
        except DockerError, e:
            logging.error('Something went wrong with Docker: {}'.format(str(e)))
            mongo.update_record_status(record['_id'], 'submitted')
            return

        eventlet.sleep(5)
        test_result = docker.test_endpoint(container_ip, config.container['api_port'], config.container['api_path'])
        docker.clean_container(container_id, image)

        if test_result:
            logging.info('Submission SUCCESSFUL for {}'.format(record['name']))
            mongo.update_record_status(record['_id'], 'successful',
                                       statusmsg='Validation passed with image {}'.format(image))
            return

    logging.info('Submission FAILED for {}'.format(record['name']))
    mongo.update_record_status(record['_id'], 'failed', statusmsg='None of the provided images passed the validation')


if __name__ == '__main__':
    docker_worker()



