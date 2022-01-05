import unittest
from unittest import mock
import argparse
import os
import tempfile
import pytest
import logging

from d20.Manual.Exceptions import ConfigNotFoundError, PlayerCreationError
from d20.Manual.GameMaster import GameMaster
from d20.Manual.RPC import (
    Entity,
    EntityType,
    RPCStreamCommands,
    RPCCommands,
    RPCStartStreamRequest,
    RPCStopStreamRequest,
    RPCRequest)
from d20.Manual.Facts import loadFacts
from d20.Manual.Templates import (registerNPC,
                                  NPCTemplate,
                                  registerBackStory,
                                  BackStoryTemplate,
                                  registerPlayer,
                                  PlayerTemplate,
                                  registerScreen,
                                  ScreenTemplate)
from d20.Manual.Trackers import PlayerTracker
from d20.Screens import Screen
from d20.Manual.Options import Arguments
from d20.version import GAME_ENGINE_VERSION_RAW
from d20.Manual.Logger import logging, DEFAULT_LEVEL
from d20.Manual.Console import PlayerState


loadFacts()

args_ex = argparse.Namespace(
    config=None,
    debug=True,
    dump_objects=None,
    extra_actions=[],
    extra_facts=[],
    extra_npcs=[],
    extra_players=[],
    extra_screens=[],
    file=None,
    backstory_facts=None,
    backstory_facts_path=None,
    info_player=None,
    list_npcs=False,
    list_players=False,
    list_screens=False,
    load_file=None,
    save_file=None,
    temporary='/tmp/d20-test',
    use_screen='json',
    verbose=False,
    version=False)


class testGameMaster(unittest.TestCase):
    def setUp(self):
        tf = tempfile.NamedTemporaryFile(delete=False)
        self.testfile = tf.name
        tf.close()

        self.args = args_ex
        self.args.file = self.testfile

    def tearDown(self):
        os.remove(self.testfile)
        del self.testfile

    def testGameMasterInsufficientArgs(self):
        with self.assertRaises(TypeError):
            GameMaster()

    def testGameMasterNoFile(self):
        with self.assertRaises(TypeError):
            del self.args.file
            GameMaster(options=self.args)

    def testGameMaster(self):
        gm = GameMaster(options=self.args)

        self.assertEqual(len(gm.objects), 1)
        self.assertGreater(len(gm.npcs), 0)
        self.assertGreater(len(gm.screens), 0)

        gm.cleanup()

    # def testLoad(self):
    #     gm = GameMaster(options=self.args)
    #     mock_npc = mock.MagicMock()
    #     mock_npc.name = "HashNPC"
    #     save_state = {
    #             "npcs": [mock_npc]
    #         }
    #     gm.save_state = save_state
    #     gm.registerNPCs(True)


class testGameMasterHandlers(unittest.TestCase):
    def setUp(self):
        tf = tempfile.NamedTemporaryFile(delete=False)
        self.testfile = tf.name
        tf.close()

        self.args = argparse.Namespace(
            config=None,
            debug=True,
            dump_objects=None,
            extra_actions=[],
            extra_facts=[],
            extra_npcs=[],
            extra_players=[],
            extra_screens=[],
            file=self.testfile,
            info_player=None,
            list_npcs=False,
            list_players=False,
            list_screens=False,
            load_file=None,
            save_file=None,
            temporary='/tmp/d20-test',
            use_screen='json',
            verbose=False,
            version=False)

        self.gm = GameMaster(options=self.args)
        #  Mock RPC so calls to it don't matter
        self.gm.rpc = mock.Mock()

    def tearDown(self):
        self.gm.cleanup()

    def testFactStreamHandlers(self):
        fact_types = ['md5', 'sha1']
        e = Entity(EntityType.npc, 1, 1)
        msg = RPCStartStreamRequest(
            e, RPCStreamCommands.factStream,
            args={'fact_types': fact_types, 'only_latest': False})
        stream_id = msg.id
        self.gm.streamHandleFactStreamStart(msg)

        for ft in fact_types:
            self.assertIn(ft, self.gm.factStreamList.keys())

        msg = RPCStopStreamRequest(e, stream_id)
        self.gm.streamHandleFactStreamStop(msg)

        for ft in fact_types:
            self.assertEqual(list(), self.gm.factStreamList[ft])

    def testHypStreamHandlers(self):
        hyp_types = ['md5', 'sha1']
        e = Entity(EntityType.npc, 1, 1)
        msg = RPCStartStreamRequest(
            e, RPCStreamCommands.hypStream,
            args={'hyp_types': hyp_types, 'only_latest': False})
        stream_id = msg.id
        self.gm.streamHandleHypStreamStart(msg)

        for ft in hyp_types:
            self.assertIn(ft, self.gm.hypStreamList.keys())

        msg = RPCStopStreamRequest(e, stream_id)
        self.gm.streamHandleHypStreamStop(msg)

        for ft in hyp_types:
            self.assertEqual(list(), self.gm.hypStreamList[ft])

    def testChildFactStreamHandlers(self):
        fact_types = ['md5', 'sha1']
        e = Entity(EntityType.npc, 1, 1)
        msg = RPCStartStreamRequest(
            e, RPCStreamCommands.childFactStream,
            args={'object_id': 1,
                  'fact_id': None,
                  'hyp_id': None,
                  'fact_types': fact_types,
                  'only_latest': False})
        stream_id = msg.id
        self.gm.streamHandleChildFactStreamStart(msg)

        for ft in fact_types:
            self.assertIn(ft, self.gm.factStreamList.keys())

        msg = RPCStopStreamRequest(e, stream_id)
        self.gm.streamHandleFactStreamStop(msg)

        for ft in fact_types:
            self.assertEqual(list(), self.gm.factStreamList[ft])

    def testChildHypStreamHandlers(self):
        hyp_types = ['md5', 'sha1']
        e = Entity(EntityType.npc, 1, 1)
        msg = RPCStartStreamRequest(
            e, RPCStreamCommands.childHypStream,
            args={'object_id': 1,
                  'fact_id': None,
                  'hyp_id': None,
                  'types': hyp_types,
                  'only_latest': False})
        stream_id = msg.id
        self.gm.streamHandleChildHypStreamStart(msg)

        for ft in hyp_types:
            self.assertIn(ft, self.gm.hypStreamList.keys())

        msg = RPCStopStreamRequest(e, stream_id)
        self.gm.streamHandleHypStreamStop(msg)

        for ft in hyp_types:
            self.assertEqual(list(), self.gm.hypStreamList[ft])

    def testChildObjectStreamHandlers(self):
        e = Entity(EntityType.npc, 1, 1)
        msg = RPCStartStreamRequest(
            e, RPCStreamCommands.childObjectStream,
            args={'object_id': 1,
                  'fact_id': None,
                  'hyp_id': None,
                  'only_latest': False})
        stream_id = msg.id
        self.gm.streamHandleChildObjectStreamStart(msg)

        self.assertIn(msg, self.gm.objectStreamList)

        msg = RPCStopStreamRequest(e, stream_id)
        self.gm.streamHandleChildObjectStreamStop(msg)

        self.assertEqual(list(), self.gm.objectStreamList)

    def testhandleAddObject1(self):
        e = Entity(EntityType.npc, 1, 1)
        msg = RPCRequest(
            e, RPCCommands.addObject,
            args={
                'object_data': b'testtesttest',
                'creator': 'test',
                'parentObjects': list(),
                'parentFacts': list(),
                'parentHyps': list(),
                'metadata': None,
                'encoding': None
            }
        )

        self.gm.handleAddObject(msg)

        e = Entity(EntityType.npc, 1, 1)
        msg = RPCRequest(
            e, RPCCommands.addObject,
            args={
                'object_data': u'\u221a25',  # <- utf-8
                'creator': 'test',
                'parentObjects': list(),
                'parentFacts': list(),
                'parentHyps': list(),
                'metadata': None,
                'encoding': None
            }
        )

        self.gm.handleAddObject(msg)

    def testhandleAddObject2(self):
        e = Entity(EntityType.npc, 1, 1)
        msg = RPCRequest(
            e, RPCCommands.addObject,
            args={
                'object_data': b'testtesttest',
                'creator': 'test',
                'parentObjects': list(),
                'parentFacts': list(),
                'parentHyps': list(),
                'metadata': None,
                # 'encoding': None
            }
        )

        self.gm.handleAddObject(msg)
        self.gm.rpc.sendErrorResponse.assert_called_once_with(
            msg, reason="'Namespace' object has no attribute 'encoding'")

    def testhandleAddObject3(self):
        e = Entity(EntityType.npc, 1, 1)
        msg1 = RPCRequest(
            e, RPCCommands.addObject,
            args={
                'object_data': b'testtesttest',
                'creator': 'test',
                'parentObjects': list(),
                'parentFacts': list(),
                'parentHyps': list(),
                'metadata': None,
                'encoding': None
            }
        )

        e = Entity(EntityType.npc, 2, 1)
        msg2 = RPCRequest(
            e, RPCCommands.addObject,
            args={
                'object_data': b'testtesttest',
                'creator': 'test',
                'parentObjects': list(),
                'parentFacts': list(),
                'parentHyps': list(),
                'metadata': None,
                'encoding': None
            }
        )

        self.gm.handleAddObject(msg1)
        self.gm.rpc.sendOKResponse.assert_called_with(
            msg1, result={'object_id': 1}
        )

        self.gm.handleAddObject(msg2)
        self.gm.rpc.sendOKResponse.assert_called_with(
            msg2, result={'object_id': 1}
        )

    @mock.patch('d20.Manual.BattleMap.FileObject.__init__')
    def testhandleAddObject4(self, FileObjectInit):
        error_string = "mock_type error"
        FileObjectInit.side_effect = TypeError(error_string)

        e = Entity(EntityType.npc, 1, 1)
        msg = RPCRequest(
            e, RPCCommands.addObject,
            args={
                'object_data': b'testtesttest',
                'creator': 'test',
                'parentObjects': list(),
                'parentFacts': list(),
                'parentHyps': list(),
                'metadata': None,
                'encoding': None
            }
        )

        self.gm.handleAddObject(msg)
        self.gm.rpc.sendErrorResponse.assert_called_with(
            msg,
            reason="Unable to track object: %s" % (error_string)
            )


def testGameMasterInitKwargs(monkeypatch):
    mock1 = mock.Mock()

    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerBackStories",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerNPCs",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerPlayers",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerScreens",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mock1)

    args = args_ex
    args.backstory_facts = "test"
    gm = GameMaster(extra_players='test',
                    extra_npcs='test',
                    extra_backstories='test',
                    extra_screens='test',
                    options=args)
    assert gm.extra_players == 'test'
    assert gm.extra_npcs == 'test'
    assert gm.extra_backstories == 'test'
    assert gm.extra_screens == 'test'

    with pytest.raises(TypeError) as excinfo:
        gm = GameMaster(test='test')
    assert str(excinfo.value) == "test is an invalid keyword argument"

    del args.temporary
    with pytest.raises(RuntimeError) as excinfo:
        gm = GameMaster(options=args)
    assert str(excinfo.value) == "Expected temporary directory to be" \
        " specified in options"
    args.temporary = '/tmp/d20-test'


def testBackStoryFactLoad1(monkeypatch):
    mockBSF = mock.Mock()
    mock1 = mock.Mock()

    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerBackStories",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerNPCs",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerPlayers",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerScreens",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mockBSF)

    args = args_ex
    args.backstory_facts = """
    facts:
        - name: BulkAnalyzeFact
          arguments:
            directory: /path/to/files
            recursive: False
            enable: True
        - name: VTDownloadFact
          arguments:
            vt_api_key: your_api_key
            filehash: hash_to_lookup_and_download_for_analysis
            enable: False
    """

    gm = GameMaster(options=args)
    mockBSF.assert_called()
    gm.cleanup()


def testBackStoryFactPathLoad2(monkeypatch):
    mockBSF = mock.Mock()
    mock1 = mock.Mock()

    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerBackStories",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerNPCs",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerPlayers",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerScreens",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mockBSF)

    tf = tempfile.NamedTemporaryFile(delete=False)
    tf.write(b"""
        facts:
            - name: BulkAnalyzeFact
              arguments:
                directory: /path/to/files
                recursive: False
                enable: True
            - name: VTDownloadFact
              arguments:
                vt_api_key: your_api_key
                filehash: hash_to_lookup_and_download_for_analysis
                enable: False
    """)

    tf.close()
    args = args_ex
    args.backstory_facts_path = tf.name

    GameMaster(options=args)
    mockBSF.assert_called()
    os.remove(tf.name)


def testFileOpenException(monkeypatch):
    exception_mock = mock.Mock(return_value=Exception)
    mock1 = mock.Mock()
    tf = tempfile.NamedTemporaryFile(delete=False)
    tf.close()
    args = args_ex
    args.file = tf.name

    with monkeypatch.context() as m:
        m.setattr('builtins.open', exception_mock)
        m.setattr('d20.Manual.GameMaster.LOGGER.exception', mock1)
        with pytest.raises(SystemExit):
            GameMaster(options=args)
        os.remove(tf.name)
    del args.file


def testRegisterNPCsError(monkeypatch, caplog):
    mock1 = mock.Mock()
    mock_exception = mock.Mock(side_effect=Exception)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerBackStories",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerPlayers",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerScreens",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mock1)
    monkeypatch.setattr("d20.Manual.Trackers.PlayerDirectoryHandler",
                        mock1)

    @registerNPC(
        name="TestNPC",
        description="Raises exception on init",
        creator="",
        version="0.1",
        engine_version="0.1"
    )
    class RegTestNPC(NPCTemplate):
        def __init__(self, **kwargs):
            raise Exception

        def handleData(self, **kwargs):
            pass

    args = args_ex
    args.backstory_facts = "test"
    GameMaster(options=args)
    assert "Unable to create NPC TestNPC ... skipping" in caplog.text

    monkeypatch.setattr("d20.Manual.Trackers.NPCTracker.createNPC",
                        mock_exception)
    GameMaster(options=args)
    assert "Unexpected issue creating NPC" in caplog.text


def testRegisterBackStories(monkeypatch, caplog):
    mock1 = mock.Mock()
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerNPCs",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerPlayers",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerScreens",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mock1)
    monkeypatch.setattr("d20.Manual.Trackers.PlayerDirectoryHandler",
                        mock1)
    monkeypatch.setattr("d20.Manual.Trackers.BackStoryTracker.load",
                        mock.Mock(return_value="Success"))

    @registerBackStory(
        name="TestBackStory",
        description="Test BackStory",
        creator="",
        version="0.1",
        engine_version="0.1",
        category="testing"
    )
    class TestBackStory(BackStoryTemplate):
        def __init__(self, **kwargs):
            raise Exception

        def handleFact(self, **kwargs):
            pass

    args = args_ex
    args.backstory_facts = "test"
    save = {'backstories': [{'name': 'TestBackStory'}]}
    gm = GameMaster(options=args, save_state=save)
    gm.registerBackStories(True)
    assert gm.backstories == ['Success']

    gm = GameMaster(options=args)
    assert "Unexpected issue creating BackStory" in caplog.text


def testRegisterPlayers(monkeypatch):
    mock1 = mock.Mock()
    mocktracker = mock.Mock(spec=PlayerTracker)
    mocktracker.name = "TestTracker"
    mocktracker.id = 1
    mocktracker.maxTurnTime = None
    mocktracker.player = mock.Mock()
    mocktracker.player.registration = mock.Mock()
    mocktracker.player.registration.factInterests = []
    mocktracker.player.registration.hypInterests = ["testinterest"]

    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerNPCs",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerBackStories",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerScreens",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mock1)
    monkeypatch.setattr("d20.Manual.Trackers.PlayerDirectoryHandler",
                        mock1)
    monkeypatch.setattr("d20.Manual.Trackers.PlayerTracker.load",
                        mock.Mock(return_value=mocktracker))

    @registerPlayer(
        name="TestPlayer",
        description="Test Player",
        creator="",
        version="0.1",
        engine_version="0.1",
        interests=['hash']
    )
    class TestPlayer(PlayerTemplate):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        def handleFact(self, **kwargs):
            pass

        def handleHyp(self, **kwargs):
            pass

    args = args_ex
    args.backstory_facts = "test"
    save = {'players': [{'name': 'TestPlayer'}]}
    gm = GameMaster(options=args, save_state=save)
    gm.registerPlayers(True)
    assert gm.players[0].name == "TestTracker"
    assert gm.hyp_interests == {'testinterest': [1]}


def testStartGame(monkeypatch, caplog):
    mock1 = mock.Mock()
    mockengage = mock.Mock()
    mockexception = mock.Mock(side_effect=Exception)

    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerBackStories",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerPlayers",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerScreens",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mock1)
    monkeypatch.setattr("threading.Thread.start", mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.engageBackStories",
                        mockengage)
    monkeypatch.setattr("d20.Manual.Trackers.NPCTracker.handleData",
                        mockexception)

    args = args_ex
    args.backstory_facts = "test"
    gm = GameMaster(options=args)
    gm.startGame()
    mockengage.assert_called()
    gm.cleanup()

    tf = tempfile.NamedTemporaryFile(delete=False)
    tf.close()
    args.file = tf.name
    gm = GameMaster(options=args)
    gm.startGame()
    mockexception.assert_called()
    assert "Error calling NPC handleData function" in caplog.text


def testEngageBackStoryError(monkeypatch, caplog):
    mock1 = mock.Mock()
    mock_backstory_facts = mock.Mock(return_value=["test"])
    mockexception = mock.Mock(side_effect=Exception)

    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerPlayers",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerScreens",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerNPCs",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mock_backstory_facts)
    monkeypatch.setattr(
        "d20.Manual.Trackers.BackStoryCategoryTracker.handleFact",
        mockexception)

    @registerBackStory(
        name="TestBackStory",
        description="Test BackStory",
        creator="",
        version="0.1",
        engine_version="0.1",
        category="testing"
    )
    class TestBackStory(BackStoryTemplate):
        def __init__(self, **kwargs):
            raise Exception

        def handleFact(self, **kwargs):
            pass

    args = args_ex
    args.file = None
    args.backstory_facts = "TestBackStory"
    gm = GameMaster(options=args)
    gm.engageBackStories()
    assert "Error calling BackStory handleFact function" in caplog.text


def testParseScreenOptions(monkeypatch):
    mock1 = mock.Mock()
    mockScreen = mock.Mock(spec=Screen)
    mockScreen.config = None

    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerPlayers",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerScreens",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerNPCs",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerBackStories",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mock1)

    args = args_ex
    args.backstory_facts = "TestBackStory"
    gm = GameMaster(options=args)
    with pytest.raises(ConfigNotFoundError):
        gm._parse_screen_options(mockScreen)

    mockScreen.config = mock.Mock()
    mockScreen.registration = mock.Mock()
    mockScreen.registration.options = mock.Mock()
    mockScreen.registration.options.parse = mock.Mock(return_value="test")
    gm = GameMaster(options=args)
    assert gm._parse_screen_options(mockScreen) == "test"


def testProvideData(monkeypatch):
    mock1 = mock.Mock()
    mockParseScreen = mock.Mock(return_value={})

    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerPlayers",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerNPCs",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerBackStories",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mock1)
    monkeypatch.setattr(
        "d20.Manual.GameMaster.GameMaster._parse_screen_options",
        mockParseScreen)

    @registerScreen(
        name="TestScreen",
        version="0.1",
        engine_version="0.1",
        options=Arguments(("test", {}))
    )
    class TestScreen(ScreenTemplate):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        def filter(self):
            return "test filter"

        def present(self):
            return "test present"

    args = args_ex
    args.backstory_facts = "TestBackStory"
    gm = GameMaster(options=args)

    with pytest.raises(ValueError) as excinfo:
        gm.provideData("Nonexist Filter")
    assert str(excinfo.value) == "No screen by that name"

    assert gm.provideData("TestScreen") == "test filter"
    assert gm.provideData("TestScreen", True) == "test present"


def testSave(monkeypatch):
    mock1 = mock.Mock()

    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerPlayers",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerScreens",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerNPCs",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerBackStories",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mock1)

    args = args_ex
    args.backstory_facts = "TestBackStory"
    gm = GameMaster(options=args)
    gm.objects = []
    save_dict = {'players': [],
                 'npcs': [],
                 'objects': [],
                 'facts': {'ids': 0, 'columns': {}},
                 'hyps': {'ids': 0, 'columns': {}},
                 'engine': GAME_ENGINE_VERSION_RAW,
                 'temp_base': '/tmp/d20-test',
                 'backstories': []}
    assert gm.save() == save_dict


def testGetEntityName(monkeypatch):
    mock1 = mock.Mock()

    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerPlayers",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerScreens",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerNPCs",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerBackStories",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mock1)

    args = args_ex
    args.backstory_facts = "TestBackStory"
    gm = GameMaster(options=args)
    mockEntity = mock.Mock()
    mockEntity.isPlayer = False
    mockEntity.isNPC = False
    mockEntity.isBackStory = False
    mockPlayer = mock.Mock()
    mockPlayer.name = "testplayer"
    gm.players = [mockPlayer]
    mockNPC = mock.Mock()
    mockNPC.name = "testnpc"
    gm.npcs = [mockNPC]
    mockBS = mock.Mock()
    mockBS.name = "testbackstory"
    gm.backstories = [mockBS]

    mockEntity.id = 0
    assert gm.getEntityName(mockEntity) == "Unknown!"

    mockEntity.isBackStory = True
    assert gm.getEntityName(mockEntity) == "testbackstory"

    mockEntity.isNPC = True
    assert gm.getEntityName(mockEntity) == "testnpc"

    mockEntity.isPlayer = True
    assert gm.getEntityName(mockEntity) == "testplayer"


def testAstopError(monkeypatch):
    mock1 = mock.Mock()

    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerPlayers",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerScreens",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerNPCs",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerBackStories",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.stop", mock1)
    monkeypatch.setattr("asyncio.new_event_loop",
                        mock.Mock(side_effect=Exception))

    args = args_ex
    args.backstory_facts = "TestBackStory"
    gm = GameMaster(options=args)

    with pytest.raises(Exception) as exc_info:
        gm.astop()
        assert str(exc_info.value) == "Exception trying to cleanup event loop"


def testStopError(monkeypatch):
    mock1 = mock.Mock()

    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerPlayers",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerScreens",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerNPCs",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerBackStories",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mock1)
    monkeypatch.setattr("d20.Manual.RPC.RPCServer.stop",
                        mock.Mock(side_effect=Exception))

    args = args_ex
    args.backstory_facts = "TestBackStory"
    gm = GameMaster(options=args)

    with pytest.raises(Exception) as exc_info:
        gm.stop()
        assert str(exc_info.value) == "Exception trying to stop GM"


def testRunGame(monkeypatch):
    mock1 = mock.Mock()

    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerPlayers",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerScreens",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerNPCs",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerBackStories",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster._reportRuntime",
                        mock1)
    monkeypatch.setattr("d20.Manual.RPC.RPCServer.stop",
                        mock.Mock(side_effect=Exception))

    args = args_ex
    args.backstory_facts = "TestBackStory"
    gm = GameMaster(options=args)

    gm.runGame()
    assert not gm.gameRunning


def testReportRuntime(monkeypatch, caplog):
    mock1 = mock.Mock()

    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerPlayers",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerScreens",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerNPCs",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerBackStories",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mock1)

    logger = logging.getLogger()
    logger.setLevel(DEFAULT_LEVEL)
    monkeypatch.setattr("d20.Manual.GameMaster.LOGGER", logger)

    args = args_ex
    args.backstory_facts = "TestBackStory"
    gm = GameMaster(options=args)

    mocknpc = mock.Mock()
    mocknpc.runtime = 1
    mocknpc.name = "testnpc"
    gm.npcs = [mocknpc]
    mockplayer = mock.Mock()
    mockplayer.runtime = 2
    mockplayer.name = "testplayer"
    gm.players = [mockplayer]

    gm._reportRuntime()
    return_text = "INFO     root:GameMaster.py:598 NPC    'testnpc   ' - " \
        "runtime  1.0000s\nINFO     root:GameMaster.py:604 Player " \
        "'testplayer' - runtime  2.0000s\n"
    assert caplog.text == return_text


def testCheckGameState(monkeypatch):
    mock1 = mock.Mock()

    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerPlayers",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerScreens",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerNPCs",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerBackStories",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mock1)

    args = args_ex
    args.backstory_facts = "TestBackStory"
    gm = GameMaster(options=args)

    gm._maxGameTime = 1
    gm._gameStartTime = 1
    assert gm.checkGameState(0)
    gm._maxGameTime = 0

    mockRunningComponent = mock.Mock()
    mockRunningComponent.state = PlayerState.running
    gm.backstory_categories = {'test': mockRunningComponent}
    assert not gm.checkGameState(0)
    gm.backstory_categories = {}

    gm.players = [mockRunningComponent]
    assert not gm.checkGameState(0)
    mockWaitingPlayer = mock.Mock()
    mockWaitingPlayer.state = PlayerState.waiting
    gm.players = [mockWaitingPlayer]
    assert gm.checkGameState(0)
    gm.players = []

    gm.npcs = [mockRunningComponent]
    assert not gm.checkGameState(0)
    gm.npcs = []

    gm._idleTicks = 0
    assert gm.checkGameState(0)

    gm._idleTicks = gm._idleCount + 1
    assert not gm.checkGameState(0)


def testHandlePrint(monkeypatch, caplog):
    mock1 = mock.Mock()
    mockEntityName = mock.Mock(return_value="testName")

    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerPlayers",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerScreens",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerNPCs",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.registerBackStories",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.resolveBackStoryFacts",
                        mock1)
    monkeypatch.setattr("d20.Manual.GameMaster.GameMaster.getEntityName",
                        mockEntityName)

    args = args_ex
    args.backstory_facts = "TestBackStory"
    gm = GameMaster(options=args)

    mockRPC = mock.Mock(spec=RPCRequest)
    mockRPC.entity = 'test'
    mockRPC.args = argparse.Namespace()
    mockErrorRsp = mock.Mock()
    monkeypatch.setattr("d20.Manual.RPC.RPCServer.sendErrorResponse",
                        mockErrorRsp)

    gm.handlePrint(mockRPC)
    mockErrorRsp.assert_called_with(mockRPC,
                                    reason="Missing required field in args")

    mockRPC.args.kwargs = None
    gm.handlePrint(mockRPC)
    mockErrorRsp.assert_called_with(mockRPC,
                                    reason="Missing required field in args")

    mockRPC.args.kwargs = {'wrongarg': 'test'}
    mockRPC.args.args = ['foo']
    gm.handlePrint(mockRPC)
    mockErrorRsp.assert_called_with(mockRPC,
                                    reason="Unexpected field in kwargs")

    class Foo(object):
        def __str__(self):
            raise Exception
    mockRPC.args.kwargs = {'sep': 'test'}
    mockRPC.args.args = [Foo()]
    gm.handlePrint(mockRPC)
    mockErrorRsp.assert_called_with(mockRPC,
                                    reason="Unable to convert "
                                    "contents to string")

    mockRPC.args.args = [Foo(), 'foo']
    gm.handlePrint(mockRPC)
    mockErrorRsp.assert_called_with(mockRPC,
                                    reason="Unable to convert "
                                    "arguments to string")

    logger = logging.getLogger()
    logger.setLevel(DEFAULT_LEVEL)
    monkeypatch.setattr("d20.Manual.GameMaster.LOGGER", logger)
    mockRPC.args.args = ['test1']
    gm.handlePrint(mockRPC)
    assert "testName: test1" in caplog.text

    mockRPC.args = None
    gm.handlePrint(mockRPC)
    mockErrorRsp.assert_called_with(mockRPC,
                                    reason="args field formatted incorrectly")
