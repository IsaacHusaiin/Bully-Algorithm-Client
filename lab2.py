"""""
Author: Isaac Yushaiyin
Filename: lab2.py
Date: Oct 17 2024
Purpose: Implement the client-side of a group of nodes in the bully algorithm,
         which communicates with a Group Coordinator Daemon (GCD) to perform leader elections.
"""
import sys
import socket
import pickle
import threading
import socketserver
import time
import random
from datetime import datetime

class ThreadedTCPServer(socketserver.ThreadingTCPServer):
    """
        ThreadedTCPServer is a custom server class that handles communication between nodes.
        It uses the bully algorithm to manage leader elections.

        Attributes:
            node_identity (tuple): Identity of the node (days_to_mother's_birthday, su_id).
            gcd_host (str): The hostname of the Group Coordination Daemon (GCD).
            gcd_port (int): The port number of the GCD.
            membership_list (dict): List of members retrieved from GCD {identity: (host, port)}.
            election_in_progress (bool): Indicates if an election is currently in progress.
            coordinator_id (tuple): Identity of the current leader node.
            lock (threading.Lock): A lock to ensure thread-safe access to shared data structures.
        """

    def __init__(self, server_address, requesthandler, gcd_host,gcd_port,node_identity):
        super().__init__(server_address, requesthandler)
        self.node_identity = node_identity
        self.gcd_host =gcd_host
        self.gcd_port = gcd_port
        self.membership_list = {}
        self.election_in_progress = False
        self.coordinator_id = None
        self.received_ok = False
        self.lock = threading.Lock()
        """
            Initialize the server and its attributes.

            Args:
                server_address (tuple): The address (host, port) on which the server will bind.
                requesthandler (class): The handler class used to manage incoming requests.
                gcd_host (str): Hostname of the GCD server.
                gcd_port (int): Port number of the GCD server.
                node_identity (tuple): The unique identity of this node (days_to_next_mother's_birthday, su_id).
            """


    def handle_leader_message(self, leader_node):
        """
                Handle the 'COORDINATOR' message received from a newly elected leader.

                Args:
                    leader_node (tuple): The identity of the new leader.
                """
        print(f"received leader message from {leader_node}")
        with self.lock:
            self.current_leader = leader_node
            self.election_in_progress = False
            print(f"New leader is {self.current_leader}")

        if hasattr(self, 'received_coordinator_event'):
            self.received_coordinator_event.set()
            print(f"Coordinator message received: {leader_node}")



    def connect_to_gcd(self):
        """
                Connect to the GCD (Group Coordination Daemon) to retrieve the list of group members.
                This method sends a 'BEGIN' message to the GCD to register the node and get the updated members list.
                """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as gcd_sock:
                gcd_sock.settimeout(5)  # Set timeout
                gcd_sock.connect((self.gcd_host, self.gcd_port))  # Connect to GCD
                message = ('BEGIN', (self.node_identity, self.server_address))

                gcd_sock.sendall(pickle.dumps(message))  # Send message to GCD
                print(f"connected to gcd: {gcd_sock.getsockname()}")
                response = gcd_sock.recv(1024)  # Receive response
                response_data = pickle.loads(response)  # Deserialize response
                print(f"received response: {response_data}")

                with self.lock:  # Ensure thread-safe access
                    self.membership_list = response_data
                print(f"Members received: {self.membership_list}")
        except Exception as e:
            print(f"Failed to connect to coordinator: {e}")  # Handle error



    def announce_leader(self):
        """
                Declare the current node as the leader and notify all other members.
                Sends a 'COORDINATOR' message to all other nodes in the membership list.
                """
        with self.lock:
            self.current_leader = self.node_identity
            self.election_in_progress = False
            print(f"New leader is {self.current_leader}")
        failed_node=[]
        for ident, addr in self.membership_list.items():
            if ident == self.node_identity:
                continue
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.setblocking(0)  #set to non-blocking mode
                    sock.settimeout(5)  # Set timeout for connection
                    sock.connect(addr)  # Connect to node
                    coordinator_message = ('COORDINATOR', self.node_identity)
                    sock.sendall(pickle.dumps(coordinator_message))  # Send coordinator message
                    print(f"sent coordinator message to {addr}")
            except Exception as e:
                print(f"Failed to connect to coordinator: {e}")
                continue  # Continue if failed to send

        #remove nodes that are failed
        with self.lock:
            for ident in failed_node:
                print(f"Removing failed node: {ident}")
                del self.membership_list[ident]




    def handle_election_message(self, sender_identity, sender_address, sender_members):
        """
        Handle receipt of an 'ELECTION' message from another node.
        Respond with an 'OK' message and start an election if one is not in progress.

        Args:
        sender_identity (tuple): The identity of the node that sent the election message.
        sender_address (tuple): The address of the sender node.
        sender_members (dict): The members list from the sender node.
        """

        print("Election message received")
        with self.lock:
            self.membership_list.update(sender_members)
            print(f"updating membership list, new members: {self.membership_list}")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)  # Set timeout
                sock.connect(sender_address)  # Connect to sender
                message = ('OK', None)
                sock.sendall(pickle.dumps(message))  # Send OK message
                print(f"sent OK message to {sender_address}")
        except Exception as e:
            print(f"failed to send election message {e}")
        if not self.election_in_progress:
            print(f"no election is in progress")
            self.initiate_election()  # Start a new election if needed


    def wait_for_leader_announcement(self):
        """
        Wait for a 'COORDINATOR' message from the new leader or start a new election if none is received.
        """
        timeout = 15
        self.received_coordinator_event = threading.Event()
        print(f"waiting for coordinator")
        coordinator_message_received = self.received_coordinator_event.wait(timeout)  # Wait for coordinator message
        if coordinator_message_received:
            print(f"Coordinator message received: {coordinator_message_received}")
        else:
            print(f"Coordinator message not received")
            with self.lock:
                self.election_in_progress = False  # Reset election status
                print(f"election is not in progress. start my own election")
                self.initiate_election()  # Start a new election


    def handle_ok_message(self):
        """
        Handle the receipt of an 'OK' message during an election process.
        """
        print(f"OK message received")





    def initiate_election(self):
        """
                Start an election by sending 'ELECTION' messages to all higher identity members.
                Wait for 'OK' messages or declare itself as the leader if no higher members are found.
        """
        with self.lock:
            if self.election_in_progress:
                print(f"election is in progress")
                return
            self.election_in_progress = True  # Mark election as in progress
            print(f"starting election: {self.node_identity}")

        self.connect_to_gcd()  # Connect to GCD to get members list

        with self.lock:
            higher_members = {ident: addr for ident, addr in self.membership_list.items() if ident > self.node_identity}
        failed_node=[]
        if not higher_members:
            print(f"no higher members, im the leader")
            self.announce_leader()  # Declare self as leader if no higher members
        else:
            print(f"higher members found: {higher_members.keys()}")
            for ident, addr in higher_members.items():
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                        sock.settimeout(5)  # Set timeout for the socket connection
                        sock.connect(addr)  # Connect to higher member
                        messages = ('ELECTION', self.node_identity, self.membership_list)
                        sock.sendall(pickle.dumps(messages))  # Send election message
                        print(f"sent election message to {addr}")
                except Exception as e:
                    print(f"failed to send election message {e}")

                    self.handle_ok_message()  # Handle OK message if election message failed
                    failed_node.append(ident)
            #remove nodes that are failed
            with self.lock:
                for indent in failed_node:
                    print(f"Removing failed node: {indent}")
                    del self.membership_list[ident]

    def request_handler(self,message):
        """
               Route incoming messages to the appropriate handler based on the message type.

               Args:
                   message (tuple): The incoming message, which consists of
                                   (message_name, message_data, members_data).
               """

        message1 = message[0]
        message1_data = message[1] if len(message) > 1 else None
        members_data = message[2] if len(message) > 2 else None

        if message1 == 'ELECTION':
            sender_identity = message1_data
            sender_address = members_data.get(sender_identity)
            self.handle_election_message(sender_identity, sender_address, members_data)  # Handle election
        elif message1 == 'COORDINATOR':
            leader_node = message1_data
            self.handle_leader_message(leader_node)  # Handle coordinator message
        elif message1 == 'OK':
            self.handle_ok_message()  # Handle OK message
        else:
            print(f"enter correct message")  # Handle unknown message


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    """
        ThreadedTCPRequestHandler processes incoming messages from other nodes
        and passes them to the server's request handler.
        """

    def handle(self):
        nodes_address = self.client_address
        try:
            data = self.request.recv(1024)  # Receive data from the client
            message = pickle.loads(data)  # Deserialize the received data
            print(f"received message from {nodes_address}")
            self.server.request_handler(message)  # Pass the message to the server's handler
        except Exception as e:
            print(f"Failed to handle request: {e}")  # Print any errors that occur

if __name__ == '__main__':
    """
        The main entry point of the program that starts the TCP server
        and initiates the leader election process for the node.
        """
    if len(sys.argv) < 4:
        print(f"Usage: python3 lab2.py gcd_port gcd_host")
        sys.exit(1)

    gcd_host = sys.argv[1]
    gcd_port = int(sys.argv[2])
    su_id = int(sys.argv[3])

    # Check if su_id is exactly 7 digits long
    if len(str(su_id)) != 7:
        print(f"Invalid SUID: {su_id}. It must be exactly 7 digits.")
        sys.exit(1)

    # Check if next birthday string is provided or use default
    if len(sys.argv) == 5:
       next_birthday_str = sys.argv[4]
    else:
        next_birthday_str = "01-01"

    try:
        mom_birthday = datetime.strptime(next_birthday_str, "%m-%d").replace(year=datetime.now().year)
        if mom_birthday < datetime.now():
            mom_birthday = mom_birthday.replace(year=datetime.now().year + 1)
        days_to_mom_birthday = (mom_birthday - datetime.now()).days
    except ValueError:
        print("Invalid date format. Use mm-dd.")
        sys.exit(1)

    node_identity = (days_to_mom_birthday, su_id)
    host_id, port_id = 'localhost', 0
    server = ThreadedTCPServer((host_id, port_id), ThreadedTCPRequestHandler, gcd_host, gcd_port, node_identity)
    host_id, port_id = server.server_address

    try:
        server_thread = threading.Thread(target=server.serve_forever)  # Start the server in a thread
        server_thread.daemon = True
        server_thread.start()
    except Exception as e:
        print(f"Failed to start server: {e}")
        sys.exit(1)

    time.sleep(1)
    server.initiate_election()  # Start election process

    try:
        while True:
            time.sleep(random.uniform(1, 5))  # Keep server running
    except KeyboardInterrupt:
        server.shutdown()
        server.server_close()
        print(f"Shutting down server")
        sys.exit(0)