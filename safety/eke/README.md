# Bellovin-Merritt Encrypted Key Exchange

This project is a proof-of-concept implementation of the Bellovin-Merritt Encrypted Key Exchange protocol. The protocol is described in the paper [Encrypted Key Exchange: Password-Based Protocols Secure Against Dictionary Attacks](https://ieeexplore.ieee.org/document/213269) by Steven M. Bellovin and Michael Merritt.

## Setup

With Python 3.10.11, execute `pip install -r requirements.txt` and you are good to go!

## Usage

Start a server using `python src/server.py`.

Then you can start a client using `python src/client.py`.

The example automatically creates a secure connection for you to send messages from client to server.

## Hazards

This is a purely academic project and should not be used in production. The multi-step protocol is not handling every error.
