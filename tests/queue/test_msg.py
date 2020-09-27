import unittest


class SingleMessageMarshallerTest(unittest.TestCase):

    def setUp(self):
        from tilequeue.queue.message import SingleMessageMarshaller
        self.msg_marshaller = SingleMessageMarshaller()

    def test_marshall_empty_list(self):
        with self.assertRaises(AssertionError):
            self.msg_marshaller.marshall([])

    def test_marshall_multiple_coords(self):
        from tilequeue.tile import deserialize_coord
        coords = map(deserialize_coord, ('1/1/1', '2/2/2'))
        with self.assertRaises(AssertionError):
            self.msg_marshaller.marshall(coords)

    def test_marshall_single_coord(self):
        from tilequeue.tile import deserialize_coord
        result = self.msg_marshaller.marshall([deserialize_coord('1/1/1')])
        self.assertEqual('1/1/1', result)

    def test_unmarshall_invalid(self):
        with self.assertRaises(AssertionError):
            self.msg_marshaller.unmarshall('invalid')

    def test_unmarshall_single(self):
        from tilequeue.tile import serialize_coord
        coords = self.msg_marshaller.unmarshall('1/1/1')
        self.assertEqual(1, len(coords))
        self.assertEqual('1/1/1', serialize_coord(coords[0]))

    def test_unmarshall_multiple(self):
        with self.assertRaises(AssertionError):
            self.msg_marshaller.unmarshall('1/1/1,2/2/2')


class MultipleMessageMarshallerTest(unittest.TestCase):

    def setUp(self):
        from tilequeue.queue.message import CommaSeparatedMarshaller
        self.msg_marshaller = CommaSeparatedMarshaller()

    def test_marshall_empty_list(self):
        actual = self.msg_marshaller.marshall([])
        self.assertEqual('', actual)

    def test_marshall_multiple_coords(self):
        from tilequeue.tile import deserialize_coord
        coords = map(deserialize_coord, ('1/1/1', '2/2/2'))
        actual = self.msg_marshaller.marshall(coords)
        self.assertEqual('1/1/1,2/2/2', actual)

    def test_marshall_single_coord(self):
        from tilequeue.tile import deserialize_coord
        result = self.msg_marshaller.marshall([deserialize_coord('1/1/1')])
        self.assertEqual('1/1/1', result)

    def test_unmarshall_invalid(self):
        with self.assertRaises(AssertionError):
            self.msg_marshaller.unmarshall('invalid')

    def test_unmarshall_empty(self):
        actual = self.msg_marshaller.unmarshall('')
        self.assertEqual([], actual)

    def test_unmarshall_single(self):
        from tilequeue.tile import serialize_coord
        coords = self.msg_marshaller.unmarshall('1/1/1')
        self.assertEqual(1, len(coords))
        self.assertEqual('1/1/1', serialize_coord(coords[0]))

    def test_unmarshall_multiple(self):
        from tilequeue.tile import deserialize_coord
        actual = self.msg_marshaller.unmarshall('1/1/1,2/2/2')
        self.assertEqual(2, len(actual))
        self.assertEqual(actual[0], deserialize_coord('1/1/1'))
        self.assertEqual(actual[1], deserialize_coord('2/2/2'))


class SingleMessageTrackerTest(unittest.TestCase):

    def setUp(self):
        from tilequeue.queue.message import SingleMessagePerCoordTracker
        self.tracker = SingleMessagePerCoordTracker()

    def test_track_and_done(self):
        from tilequeue.tile import deserialize_coord
        from tilequeue.queue.message import QueueHandle
        queue_id = 1
        queue_handle = QueueHandle(queue_id, 'handle')
        coords = [deserialize_coord('1/1/1')]
        coord_handles = self.tracker.track(queue_handle, coords)
        self.assertEqual(1, len(coord_handles))
        coord_handle = coord_handles[0]
        self.assertIs(queue_handle, coord_handle)

        track_result = self.tracker.done(coord_handle)
        self.assertIs(queue_handle, track_result.queue_handle)
        self.assertTrue(track_result.all_done)
        self.assertFalse(track_result.parent_tile)


class MultipleMessageTrackerTest(unittest.TestCase):

    def setUp(self):
        from mock import MagicMock
        from tilequeue.queue.message import MultipleMessagesPerCoordTracker
        msg_tracker_logger = MagicMock()
        self.tracker = MultipleMessagesPerCoordTracker(msg_tracker_logger)

    def test_track_and_done_invalid_coord_handle(self):
        with self.assertRaises(ValueError):
            self.tracker.done('bogus-coord-handle')

    def test_track_and_done(self):
        from tilequeue.tile import deserialize_coord
        from tilequeue.queue.message import QueueHandle
        queue_id = 1
        queue_handle = QueueHandle(queue_id, 'handle')
        coords = map(deserialize_coord, ('1/1/1', '2/2/2'))
        parent_tile = deserialize_coord('1/1/1')
        self._assert_track_done(coords, queue_handle, parent_tile)

    def test_track_and_done_not_including_parent(self):
        from tilequeue.tile import deserialize_coord
        from tilequeue.queue.message import QueueHandle
        queue_id = 1
        queue_handle = QueueHandle(queue_id, 'handle')
        coords = map(deserialize_coord, ('2/2/3', '2/2/2'))
        parent_tile = deserialize_coord('1/1/1')
        self._assert_track_done(coords, queue_handle, parent_tile)

    def _assert_track_done(self, coords, queue_handle, parent_tile):
        coord_handles = self.tracker.track(queue_handle, coords, parent_tile)
        self.assertEqual(len(coords), len(coord_handles))

        # all intermediate coords should not result in a done message.
        for coord in coord_handles[:-1]:
            track_result = self.tracker.done(coord)
            self.assertFalse(track_result.all_done)

        # final coord should complete the tracking
        track_result = self.tracker.done(coord_handles[-1])
        self.assertIs(queue_handle, track_result.queue_handle)
        self.assertTrue(track_result.all_done)
        self.assertEqual(parent_tile, track_result.parent_tile)

    def test_track_and_done_asserts_on_duplicates(self):
        from tilequeue.tile import deserialize_coord
        from tilequeue.queue.message import QueueHandle
        queue_id = 1
        queue_handle = QueueHandle(queue_id, 'handle')
        coords = map(deserialize_coord, ('2/2/2', '2/2/2'))
        parent_tile = deserialize_coord('1/1/1')

        with self.assertRaises(AssertionError):
            self.tracker.track(queue_handle, coords, parent_tile)
