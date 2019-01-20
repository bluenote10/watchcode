from __future__ import division, print_function

import datetime
import time
from watchcode.io_handler import Debouncer


def wait_with_timeout(f, timeout=5.0, cycle=0.01):
    endtime = datetime.datetime.now() + datetime.timedelta(seconds=timeout)
    while True:
        cond = f()
        if cond:
            break
        time.sleep(cycle)
        assert not datetime.datetime.now() > endtime


def test_debouncer_debounces():
    debouncer = Debouncer()
    calls = []

    def f():
        print("Hello world")
        calls.append(datetime.datetime.now())

    debouncer.trigger(f, 0.5, enqueue=True)
    time.sleep(0.1)
    debouncer.trigger(f, 0.5, enqueue=True)
    time.sleep(0.1)
    debouncer.trigger(f, 0.5, enqueue=True)

    wait_with_timeout(lambda: len(calls) > 0)
    time.sleep(0.5)

    print(calls)
    assert len(calls) == 1


def test_debouncer_updates_func():
    debouncer = Debouncer()
    calls = []

    def f1():
        print("Hello world")
        calls.append("f1")

    def f2():
        print("Hello world")
        calls.append("f2")

    def f3():
        print("Hello world")
        calls.append("f3")

    debouncer.trigger(f1, 0.5, enqueue=True)
    time.sleep(0.1)
    debouncer.trigger(f2, 0.5, enqueue=True)
    time.sleep(0.1)
    debouncer.trigger(f3, 0.5, enqueue=True)

    wait_with_timeout(lambda: len(calls) > 0)
    time.sleep(0.5)

    print(calls)
    assert len(calls) == 1
    assert calls[0] == "f3"

    debouncer.trigger(f1, 0.001, enqueue=True)
    wait_with_timeout(lambda: len(calls) > 1)
    assert calls[-1] == "f1"


def test_debouncer_enqueues():
    debouncer = Debouncer()
    calls = []

    def f():
        time.sleep(0.2)
        print("Hello world")
        calls.append(datetime.datetime.now())

    debouncer.trigger(f, 0.001, enqueue=True)
    time.sleep(0.1)
    debouncer.trigger(f, 0.001, enqueue=True)

    time.sleep(0.6)
    print(calls)
    assert len(calls) == 2


def test_debouncer_enqueues_not():
    debouncer = Debouncer()
    calls = []

    def f():
        time.sleep(0.2)
        print("Hello world")
        calls.append(datetime.datetime.now())

    debouncer.trigger(f, 0.001, enqueue=False)
    time.sleep(0.1)
    debouncer.trigger(f, 0.001, enqueue=False)

    time.sleep(0.6)
    print(calls)
    assert len(calls) == 1
