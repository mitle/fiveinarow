# Five in a row, Gomoku game in python

The well known five in a row game implemented in python using pygame. Two players can play the game, the game instances are connected by network using ZeroMQ.

## Install:

Python3 required.

use 'setup.py install' for system wide installation or clone, install required packages with pip, and run client.py/server.py

#### Required packages

* zmq
* numpy
* cryptography
* rsa
* pygame

## Usage and controls

Default values of grid size, number in a row, custom colors and communication port can be configured via the JSON config file (config.txt) editable by any text editor.


After starting both server and client on a local network.
Enter player names.
You can change board size and port on the server side, or leave the values default. If an invalid value is entered, the input box changes to red color, and can not start server.
Press start server. The server is now listening for connection.

In the client enter ip address of the server, use <ip>:<port> format if the port was changed from the default. The client will check if the given text is a possible ip address.
Press start game.


Hostname can be entered too, and non-local connections are supported if the client has internet access and the server network has public IP address and correct port forwarding setup.
Pressing enter will start connection and the game. Starting player can be set up in the instance's python file.

In the top left corner an indicator shows who is on turn. That player can place a move by clicking on the grid with mouse. After a successful (allowed) move, it is the other player's turn.

If the game ends, big message is shown, the game timer is freezed and the scoreboard is updated. A new game button appears, if both players press it a new game begins.

Anytime during the game pressing M key will toggle mute of all sounds.

## Documentation:
https://docs.google.com/document/d/1TPv9voaPbGxxiek1CzVrvMTqDQRcO5imVPn9ReHwDKI/edit?usp=sharing

## Snapshots
![Alt text](docs/config.png?raw=true)
![Alt text](docs/connecting.png?raw=true)
![Alt text](docs/in_game.png?raw=true)
![Alt text](docs/game_over.png?raw=true)