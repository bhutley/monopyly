import os
import sys
import importlib.util
import inspect


def _is_ai_package(package_folder):
    '''
    Returns True if the folder passed in is a Python package, ie a
    folder holding an __init__.py.
    '''
    if os.path.basename(package_folder) == "__pycache__":
        return False

    return os.path.isfile(os.path.join(package_folder, "__init__.py"))


def _load_package(package_name, package_folder):
    '''
    Loads the package in the folder passed in and returns the module object.

    This is the replacement for the removed imp.load_package(). The package is
    registered in sys.modules before it is executed, so that relative imports
    inside it (eg "from .sophie import SophieAI") resolve.
    '''
    init_file = os.path.join(package_folder, "__init__.py")
    spec = importlib.util.spec_from_file_location(
        package_name,
        init_file,
        submodule_search_locations=[package_folder])
    if spec is None or spec.loader is None:
        raise ImportError("Could not load the AI package: {0}".format(package_folder))

    package = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = package
    spec.loader.exec_module(package)
    return package


def _find_derived_classes(package, base_class):
    '''
    Finds classes exposed by the package which derive from base_class.

    An *instance* of each object of the types found is returned in
    a list.
    '''
    results = []

    # We look through the members of the package...
    members = inspect.getmembers(package)
    for member in members:
        try:
            # We check if the member is a class...
            member_type = member[1]
            if not inspect.isclass(member_type):
                continue

            # It is a class, so we create an instance to check
            # if it is derived from base_class...
            instance = member_type()
            if isinstance(instance, base_class):
                results.append(instance)
        except:
            continue

    return results


def load_ais():
    '''
    Finds packages containing AIs from the root->AIs folder and returns
    a list of the AI objects they contain.
    '''
    from ..game import PlayerAIBase

    # We find the AI package folders, which live in the "AIs" folder.
    # We ignore anything which is not a package, ie loose files such as
    # .DS_Store as well as __pycache__ folders...
    ai_folders = [item for item in os.listdir("AIs") if _is_ai_package("AIs/" + item)]

    # We loop through the packages...
    ais = []
    for ai_folder in ai_folders:
        # We load each package...
        package_folder = "AIs/" + ai_folder
        ai_package = _load_package(ai_folder, package_folder)

        # We find the classes they expose that are derived from the
        # base AI class...
        ais_in_package = _find_derived_classes(ai_package, PlayerAIBase)
        ais.extend(ais_in_package)

    return ais