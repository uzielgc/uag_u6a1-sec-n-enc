"""
    Assigment for U6 A1: Seguridad y encriptado.

    Author: Eloy Uziel García Cisneros (eloy.garcia@edu.uag.mx)

    usage: python node.py [-s]

"""

from network import Client, Server
import argparse

import logging

logging.basicConfig(level='INFO')

# Initialize parser
PARSER = argparse.ArgumentParser()
# set argument to identify if process will run as message broker.
PARSER.add_argument("-s", "--server", action='store_true')
ARGS = PARSER.parse_args()


if ARGS.server:
    server = Server()
    server.start_server()

client = Client()
