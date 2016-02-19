import eventlet

eventlet.monkey_patch()  # NOQA

import app_config as config
from dbController import DbDriver
from dockerController import DockerController
import logging
import click
import signal

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
@click.option('--submissions', default=5, help='Number of submissions to be processed per interval (Default: 5)')
@click.option('--interval', default=10, help='Interval used to process new submissions Default: 30)')
def docker_worker(submissions, interval):
    pool = eventlet.GreenPool(size=100)
    killer = GracefulKiller()

    while True:
        try:
            for _ in xrange(submissions):
                pool.spawn(check_submission)
            logging.info('Waiting for {} seconds'.format(interval))
            eventlet.sleep(interval)
        except (SystemExit, KeyboardInterrupt):
            break
        if killer.kill_now:
            break


def check_submission():
    mongo = DbDriver(config.database)
    docker = DockerController(config.docker['api'])
    record = mongo.get_one_record()

    if not record:
        logging.info("Quiting. No new submission.")
        return

    for image in record['repo']:
        logging.info("Downloading image {} for user {}".format(image, record['name']))
        if not docker.download_image(image_name=image):
            break

        logging.info('Starting container {} for user {}'.format(image, record['name']))
        container_id, container_ip = docker.run_container(image)

        test_result = docker.test_endpoint(container_ip, config.container['api_port'], config.container['api_path'])
        docker.clean_container(container_id, image)

        if test_result:
            logging.info('Submission SUCCESSFUL for {}'.format(record['name']))
            mongo.update_record_status(record['_id'], 'successful')
            break

    logging.info('Submission FAILED for {}'.format(record['name']))
    mongo.update_record_status(record['_id'], 'failed')


if __name__ == '__main__':
    docker_worker()



