import os
import signal
import subprocess
from random import sample
from json import loads, dumps
from socket import socket, SO_REUSEADDR, SOL_SOCKET
from urllib.request import urlopen, urlretrieve

check_data_folder = 'check_data'


class bcolors:  # for printing in terminal with colours
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def get_result(return_val, out, outfile):
    if return_val == -1:
        result = 'Timeout'
        print(bcolors.OKBLUE + result + bcolors.ENDC)
    elif return_val != 0:
        print('ERROR: Return value non zero: ', return_val)
        result = 'Error'
        print(bcolors.WARNING + result + bcolors.ENDC)
    elif return_val == 0:
        if check_execution(out, outfile):
            result = 'Correct'
            print(bcolors.OKGREEN + result + bcolors.ENDC)
        else:
            result = 'Incorrect'
            print(bcolors.FAIL + result + bcolors.ENDC)
    else:
        result = 'Contact host. Something wierd is happening to your code.'
    return result


def get_random_string(l=10):
    "Returns a string of random alphabets of 'l' length"
    return ''.join(sample('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', l))


def get_file_from_url(url, folder, overwrite=False):
    "Get file from url. Overwrite if overwrite-True"
    global check_data_folder
    # create storage path
    path = os.path.join(check_data_folder, folder)
    if not os.path.exists(path):
        os.makedirs(path)
    # get file name
    filename = url.split('/')[-1]
    if not overwrite and os.path.exists(filename):
        salt = get_random_string()
        filename = salt + filename
    # get resources
    complete_path = os.path.join(path, filename)
    fl_name, _ = urlretrieve(url, complete_path)
    return os.path.join(os.getcwd(), fl_name)


def get_json(url):
    "Get json from url and return dict"
    page = urlopen(url)
    text = page.read().decode()
    data = loads(text)
    return data


def check_execution(out_expected, outfile, check_error=None):
    "Check if output is correct."
    # get output files
    with open(out_expected, 'r') as f:
        lines_expected = f.readlines()
    with open(outfile, 'r') as f:
        lines_got = f.readlines()
    # check line by line
    for got, exp in zip(lines_got, lines_expected):
        if check_error is None:  # exact checking
            if exp.strip() != got.strip():
                return False
        else:  # error range checking
            if abs(eval(exp.strip()) - eval(got.strip())) > eval(check_error):
                return False
    return True


def run_command(cmd, timeout=30):
    "Run the command and wait for timeout time before killing"
    class Timeout(Exception):  # class for timeout exception
        pass

    def alarm_handler(signum, frame):
        "Raise the alarm of timeout"
        raise Timeout

    proc = subprocess.Popen(cmd,
                            stderr=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            shell=True
                            )

    signal.signal(signal.SIGALRM, alarm_handler)
    signal.alarm(timeout)  # 5 minutes
    try:
        stdoutdata, stderrdata = proc.communicate()
        signal.alarm(0)  # reset the alarm
    except Timeout:
        proc.terminate()
        ret_val = -1
        stderrdata = b''
    else:
        ret_val = proc.returncode
    return ret_val, stderrdata.decode()


class Slave:
    def __init__(self,
                 webserver='127.0.0.1:8000',  # where is the webserver
                 language_url='/question/detail_list/',  # what us the language data url
                 listen_addr=('127.0.0.1', 9000),  # where should this slave listen
                 timeout_limit=10  # how long to wait for timeout?
                 ):
        self.name = 'joblist_' + str(listen_addr[1])  # name of slave listening at assigned port
        print('Waking up the slave')
        self.addr = listen_addr
        self.web = webserver
        self.lang_url = language_url
        self.timeout_limit = timeout_limit
        self.processes = []
        self.sock = socket()
        # ----------------------
        self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.sock.bind(self.addr)
        self.sock.listen(5)
        print('The slave is learning about the contest.')
        self.check_data = self.__setup()
        print('Slave awaiting orders at: ', self.sock.getsockname())
        self.job_list = self.__load_jobs()

    def __load_jobs(self):
        "Load jobs according to self name"
        try:
            with open(self.name, 'r') as fl:
                data = loads(fl.read())
        except:
            data = {}
        return data

    def __shutdown(self):
        # kill existing jobs
        print('Abandoning all running checks')
        for i in self.processes:
            os.kill(i, 1)
        print('Cutting all communications')
        # close comms
        self.sock.close()
        # save job list
        with open(self.name, 'w') as fl:
            data = dumps(self.job_list)
            fl.write(data)

    def __setup(self):
        "Obtain language data and question data"
        url = 'http://' + self.web + self.lang_url
        data = get_json(url)
        print('Questions obtained:')
        base_url = 'http://' + self.web
        for q in data['question'].keys():
            # input file
            url = base_url + data['question'][q]['inp']
            data['question'][q]['inp'] = get_file_from_url(url, 'inputs')
            # output file
            url = base_url + data['question'][q]['out']
            data['question'][q]['out'] = get_file_from_url(url, 'outputs')
            print(q)
        print('Languages obtained')
        for l in data['language'].keys():
            url = base_url + data['language'][l]['wrap']
            data['language'][l]['wrap'] = get_file_from_url(url, 'wrappers')
            print(l)
        return data

    def __process_request(self, data):
        # TODO: check if question exists in case someone is malicious
        # TODO:implement timeout mechanism
        # setup
        global check_data_folder
        print('Prepping for check')
        lang, qno = str(data['language']), str(data['qno'])

        wrap = self.check_data['language'][lang]['wrap']
        inp = self.check_data['question'][qno]['inp']
        out = self.check_data['question'][qno]['out']

        overwrite = self.check_data['language'][lang]['overwrite']
        url = 'http://' + self.web + data['source']
        source = get_file_from_url(url, 'source', overwrite)

        outfile = check_data_folder + '/temp/OUT_' + get_random_string()

        permissions_modifier = 'chmod u+x ' + wrap + ';\n'
        print('Generating command:')
        command = ' '.join((permissions_modifier, wrap, inp, source, outfile))
        print(command)
        # ---------------------------------------
        print('Executing')
        return_val, stderr = run_command(command, self.timeout_limit)
        result = get_result(return_val, out, outfile)
        remarks = stderr
        print(bcolors.BOLD + remarks + bcolors.ENDC)
        print('-'*50)
        return result, remarks

    def run(self):
        while True:
            try:
                com, ard = self.sock.accept()
                data = com.recv(4096)
                data = loads(data.decode())
                if data['pk'] not in self.job_list.keys():  # First time for processing
                    result = self.__process_request(data)
                    self.job_list[data['pk']] = result  # add to joblist
                    result = dumps(result)
                else:  # not first time
                    result = dumps(self.job_list[data['pk']])
                com.sendall(result.encode('utf-8'))
                com.close()
            except KeyboardInterrupt:
                print('The slave is retiring')
                self.__shutdown()
                print('The slave is dead.')

if __name__ == '__main__':
    sl = Slave()
    sl.run()