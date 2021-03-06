from optparse import OptionParser

from generate import new_scene

from basic import *

from lang import localize


VERSION = "0.20.15"

ACTIONS = ['install', 'debug', 'package', 'deploy', 'log',
           'emulator', 'clean', 'start', 'remove', 'new_scene', 'localize', 'stop']

QUIET = True

def is_app_dir(dest_dir):
    return os.path.exists(os.path.join(dest_dir, "appinfo.json"))

def main_func():

    usage = """usage: %prog [options] action

Use PyPalm to control your development process on the webOS device.

    install - Install the current version of the app on the device
    package - Package the current version
    deploy - Package, deploy and start the app on the device
    debug - Start the debugger
    log - Get log output from the device
    clean - Remove old .ipk files
    remove - Uninstall the application
    start - Start the application on the device
    stop - Kill the application
    new_scene name - Create a new scene named 'name'
    emulator - Start the emulator
    localize - Create or update localization files"""

    usage += "\n\n    v%s (c) Martin Grund\n" % VERSION
    
    parser = OptionParser(usage)
    parser.add_option("-d", "--device", dest='device',
                      help="Target device: [tcp|usb]", default="tcp")
    parser.add_option("-f", "--follow", dest='follow',
                      help="Follow log file", action="store_true")
    parser.add_option("-i", "--version", dest="version",
                      help="Version to install", default=None)
    parser.add_option("-v", "--verbose", dest="verbose", action="store_true",
                      help="Print verbose output")
    
    (options, args) = parser.parse_args()
    
    # Get the action arg
    if len(args) == 0:
        parser.print_help()
        exit()

    # If this is not an app dir exit
    if not is_app_dir(os.getcwd()):
        print "This is not a Palm webOS application directory!"
        exit()


    # Check for the output
    if options.verbose:
        QUIET = False
    else:
        QUIET = True


    if not args[0] in ACTIONS:
        parser.error("%s must be one of: %s" % (args[0], ", ".join(ACTIONS)))

    # We always assume this dir
    current_dir = os.getcwd()
    app_info = parse_appinfo(current_dir)

    if args[0] == "package":
        package(current_dir, app_info, quiet=QUIET)
    elif args[0] == "install":
        install(current_dir, app_info, version=options.version,
                device=options.device, quiet=QUIET)
    elif args[0] == 'emulator':
        emulator()
    elif args[0] == 'log':
        log(app_info, device=options.device, follow=options.follow)
    elif args[0] == "deploy":
        package(current_dir, app_info, quiet=QUIET)
        install(current_dir, app_info, version=options.version,
                device=options.device, quiet=QUIET)
        start(current_dir, app_info['id'], device=options.device)
    elif args[0] == "debug":
        debug(app_info)
    elif args[0] == 'clean':
        clean(current_dir, app_info)
    elif args[0] == 'start':
        start(current_dir, app_info['id'], device=options.device)
    elif args[0] == "stop":
        stop(current_dir, app_info['id'], device=options.device)
    elif args[0] == 'remove':
        remove(current_dir, app_info['id'], device=options.device, quiet=QUIET)
    elif args[0] == "new_scene":
        if len(args) < 2:
            print "new_scene needs an additional 'name' argument"
            exit()
        new_scene(current_dir, args[1], quiet=QUIET)
    elif args[0] == "localize":
        localize(current_dir, quiet=QUIET)
        
if __name__ == '__main__':
    main_func()