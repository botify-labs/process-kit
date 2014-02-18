# Process-kit


## What?
process-kit is an alternative implementation of the python ``multiprocessing.Process`` standard library class.
It aspires to provide 

## Why

Although ``multiprocessing.Process`` code base is pretty robust, it felt like not being explicit nor obvious enough. Moreover, the whole design of the standard library class looks like it has been made with the whole multiprocessing library in mind rather than a clean interface to unix processes.

So we've decided to try to clean it a bit, simplify it, and make it more obvious; by getting rid of the global variables, private classes, and pretty complicated abstractions imbrications we had found in there.

#### Additional resources for the curious

* Process-kit presentation: https://speakerdeck.com/botify/fixing-the-process
* Blog post about the what, the why, and the how: https://labs.botify.com/blog/process-kit-fixing-process/


## Installation

Easy as:

```bash
pip install process-kit
```

## Usage

### The Process class

#### How to

Just like the ``multiprocessing.Process`` class, there are two different ways to run a task into a unix process using process-kit:
    - By providing a callable ``target`` to it at construction.
    - By overriding it's run method.

#### Providing a target callable

```python
from pkit.process import Process

def mytarget(*args, **kwargs):
    do_something()

proc = Process(target=mytarget, args=("abc 123",))
proc.start()
proc.join()
```

#### Overriding Process.run method

```python
from pkit.process import Process

class MyProcessObj(Process):
    def run(self, *args, **args):
        do_something()
        
my_process_obj = MyProcessObj()
my_process_obj.start()
my_process_obj.join()
```

### Augmented features

#### Reusability

Processes are cleaned up once their execution is over. They are hulls for your executions pieces. It means that once a process is collected, it's execution context attributes are reset and you can reuse it for other purpose. 

```python
import time

from pkit.process import Process

process = pkit.Process(target=lambda: time.sleep(1))
pid = process.start(wait=True)
assert pid is not None

exitcode = process.join()

assert process.pid is None
assert exitcode == 0
```


#### Blocking start

Passing the ``wait`` option to ``Process.start`` will ensure you the method call will block until the underlying process is ready to start it's execution. 

```python
import os
import time
import signal
from pkit.process import Process

process = Process(target=lambda: time.sleep(10))
process.start(wait=True)
os.kill(process.pid, signal.SIGTERM)
assert process.is_alive() is False
```

#### Blocking terminate

Passing the ``wait`` option to ``Process.terminate`` will ensure you the method call will block until the underlying process is actually stopped. As ``terminate()`` method uses a *SIGTERM* signal under the hood, it ensures you the call will block until the *SIGTERM* has been processed.

```python
import time
from pkit.process import Process

process = Process(target=lambda: time.sleep(10))
process.start()
process.terminate(wait=True)
assert process.is_alive() is False
```

#### Exit callbacks

``pkit.Process`` class exposes an **on_exit** callback option. Pass it a callable taking a single proc argument, and it will be executed as soon as the process terminates

```python
import time

from pkit.process import Process


EXITED_PID = None


def exit_callback(proc):
	EXITED_PID = proc.pid


process = Process(target=lambda: time.sleep(1), on_exit=exit_callback)
pid = process.start()
process.terminate()

assert EXITED_PID == pid
```

#### Restartable

Processes are restartable following a provided policy: forced shutdown or graceful termination.

```python
import time

from pkit.process import Process


EXITED_PID = None


def exit_callback(proc):
	EXITED_PID = proc.pid


process = Process(target=lambda: time.sleep(1), on_exit=exit_callback)
pid = process.start()
process.terminate()

assert EXITED_PID == pid
```
