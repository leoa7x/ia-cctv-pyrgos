from app.config.settings import _parse_cameras


def test_parse_cameras_supports_multiple_entries():
    cameras = _parse_cameras(
        "cam-a|rtsp://127.0.0.1:8554/a|Entrada;cam-b|rtsp://127.0.0.1:8554/b|Drone",
        "",
    )

    assert len(cameras) == 2
    assert cameras[0].camera_id == "cam-a"
    assert cameras[0].stream_url == "rtsp://127.0.0.1:8554/a"
    assert cameras[0].display_name == "Entrada"
    assert cameras[1].camera_id == "cam-b"
    assert cameras[1].display_name == "Drone"


def test_parse_cameras_falls_back_to_single_stream_url():
    cameras = _parse_cameras("", "rtsp://127.0.0.1:8554/tapo_c200")

    assert len(cameras) == 1
    assert cameras[0].camera_id == "cam-1"
    assert cameras[0].stream_url == "rtsp://127.0.0.1:8554/tapo_c200"
