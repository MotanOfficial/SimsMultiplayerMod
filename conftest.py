PATH_ROOT = None
CLIENT_SCRIPTS = None


def _add_project_paths():
    import os
    import sys

    global PATH_ROOT
    global CLIENT_SCRIPTS
    if PATH_ROOT is not None:
        return
    PATH_ROOT = os.path.dirname(os.path.abspath(__file__))
    CLIENT_SCRIPTS = os.path.join(PATH_ROOT, "client_mod", "scripts")
    protocol_dir = os.path.join(PATH_ROOT, "protocol")
    for entry in (PATH_ROOT, protocol_dir, CLIENT_SCRIPTS):
        if entry not in sys.path:
            sys.path.insert(0, entry)


_add_project_paths()