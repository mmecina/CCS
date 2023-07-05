#!/usr/bin/env python3

"""
General purpose socket communication utilities

"""
import queue
import select
import socket
import threading
import time


class Connector:
    """
    Utility class for bidirectional socket handling
    """

    RECV_NBYTES = 4096

    def __init__(self, host, port, is_server=False, response_to=2, recv_nbytes_min=0, save_to_file=None, msgdecoding='hex', resp_decoder=None):

        self.sock_timeout = 10
        self.response_to = response_to
        self.host = host
        self.port = port
        self.isserver = is_server
        self.recv_nbytes_min = recv_nbytes_min
        self.msgdecoding = msgdecoding
        self.resp_decoder = resp_decoder

        self.conn = None
        self.log = []
        self._storagefd = None

        self.receiver = None

        self._startup(save_to_file)

    def _startup(self, save_to):

        self.setup_port()
        if save_to is not None:
            self.setup_storage(save_to)

    def setup_storage(self, fname):
        self._storagefd = open(fname, 'w')

    def setup_port(self):

        self.sockfd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sockfd.settimeout(self.sock_timeout)

        if self.isserver:
            self.sockfd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sockfd.bind((self.host, self.port))
            self.sockfd.listen()
            print('Listening for connections on {}:{}'.format(self.host, self.port))

    def _connect(self):

        if self.isserver:
            self.conn, addr = self.sockfd.accept()
            print('Got connection on {}:{}'.format(self.host, self.port))
        else:
            self.sockfd.connect((self.host, self.port))
            self.conn = self.sockfd
            print('Connected to {}:{}'.format(self.host, self.port))

        self.conn.settimeout(self.response_to)

    def _close(self, servershtdwn):
        self.conn.close()
        print('Closed connection to {}:{}'.format(self.host, self.port))

        if servershtdwn:
            print('Closing server {}'.format(self.sockfd.getsockname()))
            self.sockfd.close()

    def connect(self):
        if self.conn is not None and self.conn.fileno() < 0:
            self.setup_port()
        self._connect()

    def close(self):
        self._close(False)

    def close_server(self):
        if self.isserver:
            self._close(True)
        else:
            print('Not a server')

    def close_storage(self):
        if self._storagefd is None:
            print('No file to close')
            return

        self._storagefd.close()
        self._storagefd = None

    def dump_log(self, fname, hexsep=''):
        log = '\n'.join(['{:.3f}\t{}\t{}'.format(t, _msgdecoder(msg, self.msgdecoding, sep=hexsep), _msgdecoder(resp, self.msgdecoding, sep=hexsep)) for (t, msg, resp) in self.log])
        with open(fname, 'w') as fd:
            fd.write(log)

    def send(self, msg, rx=True, output=False):

        if hasattr(msg, 'raw'):
            msg = msg.raw

        if self.conn is not None:
            self.conn.sendall(msg)
            t = time.time()

            resp = b''
            if rx:
                resp = self._recv_response()

            self.log.append((t, msg, resp))

            if self._storagefd is not None:
                self._storagefd.write('{:.3f}\t{}\t{}\n'.format(t, _msgdecoder(msg, self.msgdecoding), _msgdecoder(resp, self.msgdecoding)))
                self._storagefd.flush()

            if output:
                print('{:.3f}: SENT {} | RECV: {}'.format(t, _msgdecoder(msg, self.msgdecoding), _msgdecoder(resp, self.msgdecoding)))

            return resp if self.resp_decoder is None else self.resp_decoder(resp)

        else:
            print('Not connected!')

    def recv(self, nbytes=None):

        if nbytes is None and self.recv_nbytes_min != 0:
            nbytes = self.recv_nbytes_min
        elif nbytes is None:
            nbytes = self.RECV_NBYTES

        return self.conn.recv(nbytes)

    def _recv_response(self):

        data = b''

        try:
            if self.recv_nbytes_min != 0:
                while len(data) < self.recv_nbytes_min:
                    data += self.conn.recv(self.recv_nbytes_min - len(data))
            else:
                data += self.conn.recv(self.RECV_NBYTES)
        except Exception as err:
            print('No/invalid response ({})'.format(err))
        finally:
            return data

    def set_response_to(self, seconds):
        self.conn.settimeout(seconds)
        self.response_to = seconds

    def start_receiver(self, procfunc=None):
        """

        :param procfunc: function that must return a list
        :return:
        """
        if self.conn is None:
            print('No connection')
            return

        if self.receiver is None:
            self.receiver = Receiver([self.conn], procfunc=procfunc)
            self.receiver.start()
        else:
            print('Receiver already initialised')


class Receiver:
    """
    Reads and processes data from sockets
    """

    RECV_BYTES = 4096
    SEL_TIMEOUT = 2
    RECV_BUF_SIZE = 1024**3

    def __init__(self, sockfds, procfunc=None, recv_buf_size=RECV_BUF_SIZE):

        self.sockfds = sockfds
        self.recvd_data_buf = queue.Queue(recv_buf_size)
        self._procfunc = procfunc
        self._recv_thread = None
        self._proc_thread = None
        self.proc_data = []

        self._isrunning = False

    def start(self):
        if (self._recv_thread is None) or (not self._recv_thread.is_alive()):
            self._start_recv()
        else:
            print('Already running!')

        if self._procfunc is not None:
            if (self._proc_thread is None) or (not self._proc_thread.is_alive()):
                self._start_processing()

    def stop(self):
        self._isrunning = False

    def _start_recv(self):
        self._isrunning = True
        self._recv_thread = threading.Thread(target=self._recv_worker, name='recv_worker')
        self._recv_thread.start()

    def _recv_worker(self):

        for sockfd in self.sockfds:
            if sockfd is not None:
                print('Receiving from socket {}:{}'.format(*sockfd.getpeername()))
            else:
                self.sockfds.remove(sockfd)

        while self._isrunning:
            try:
                rd, wr, er = select.select(self.sockfds, [], self.sockfds, self.SEL_TIMEOUT)
                for sock in rd:
                    self.recvd_data_buf.put((time.time(), sock.recv(self.RECV_BYTES)))
                    # print(self.recvd_data.get())

                for sock in er:
                    print('Error in {}'.format(sock.getpeername()))
                    self.sockfds.remove(sock)
                    if not self.sockfds:
                        self.stop()

            except socket.timeout:
                continue

            except (ValueError, OSError):
                self.stop()
                break

        # for sockfd in self.sockfds:
        #     print('Stopped receiving from socket {}:{}'.format(*sockfd.getpeername()))
        print('Receiving stopped')

    def _start_processing(self):
        self._proc_thread = threading.Thread(target=self._proc_worker, name='proc_worker')
        self._proc_thread.daemon = True
        self._proc_thread.start()

    def _proc_worker(self):
        while self._isrunning:
            try:
                t, data = self.recvd_data_buf.get(timeout=1)
                self.proc_data += self._procfunc(data)
            except queue.Empty:
                continue
            except Exception as err:
                print(err)
                print('Processing stopped')
                break


def _msgdecoder(msg, fmt, sep=''):
    if fmt == 'hex':
        return hexify(msg, sep=sep)
    elif fmt == 'ascii':
        return toascii(msg)
    else:
        raise NotImplementedError('Unknown decoding style {}'.format(fmt))


def hexify(bs, sep=''):
    if bs is None:
        bs = b''
    return bs.hex().upper() if sep == '' else bs.hex(sep).upper()


def toascii(bs, errors='replace'):
    return bs.decode('ascii', errors=errors)