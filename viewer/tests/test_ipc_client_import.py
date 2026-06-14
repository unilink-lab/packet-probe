def test_ipc_client_module_imports():
    import packet_probe_viewer.ipc_client
    assert packet_probe_viewer.ipc_client.IpcClientWorker is not None
