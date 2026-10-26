import threading
import time
import unittest

from inference_queue import InferenceQueue


class InferenceQueueTests(unittest.TestCase):
    def test_interactive_request_precedes_waiting_background_job(self):
        queue = InferenceQueue()
        acquired = []
        background_started, interactive_started = threading.Event(), threading.Event()

        def work(priority, started):
            started.set()
            with queue.acquire(priority, 2):
                acquired.append(priority)

        with queue.acquire('interactive', 2):
            bg = threading.Thread(target=work, args=('background', background_started))
            fg = threading.Thread(target=work, args=('interactive', interactive_started))
            bg.start()
            self.assertTrue(background_started.wait(1))
            fg.start()
            self.assertTrue(interactive_started.wait(1))
            deadline = time.monotonic() + 1
            while queue.esperas_interactivas == 0 and time.monotonic() < deadline:
                threading.Event().wait(.001)
        fg.join(2)
        bg.join(2)
        self.assertEqual(acquired, ['interactive', 'background'])

    def test_timeout_and_exception_do_not_lock_out_later_requests(self):
        queue = InferenceQueue()
        errors = []

        def wait_for_busy_queue():
            try:
                with queue.acquire('interactive', .01):
                    self.fail('Debió agotar su tiempo en la cola.')
            except TimeoutError:
                errors.append('timeout')

        with queue.acquire('interactive', 1):
            waiter = threading.Thread(target=wait_for_busy_queue)
            waiter.start()
            waiter.join(1)
        self.assertEqual(errors, ['timeout'])
        self.assertEqual(queue.esperas_interactivas, 0)
        with self.assertRaises(ValueError):
            with queue.acquire('interactive', 1):
                raise ValueError('Error de inferencia')
        with queue.acquire('interactive', 1) as remaining:
            self.assertGreater(remaining, 0)


if __name__ == '__main__':
    unittest.main()
