# -*- coding: utf-8 -*-

import codecs
import json
import os
import re
import sys

QUIET = False

def get_files(current_dir):
    """ Get a list of .js files as tuples of (relative_path, absolute_path). """
    log("Reading file list")
    files = []
    for root, dirs, fs in os.walk(current_dir):
        for dir in dirs:
            if dir.startswith('.') or dir == "CVS":
                # Don't descend into hidden directories or CVS administrative dirs
                dirs.remove(dir)

        # Get all JS files
        for f in fs:
            if os.path.splitext(f)[1] == ".js":
                files.append((f, os.path.join(root, f)))

    return files


def process_js_files(files):
    """ Create a dict of the form {key: {fname1: 1, fname2: 1}, key2:...}. """
    lang_dict = {}
    # Matches $L("A string")
    simple_string_regexp = re.compile(r"""
        \$L\(                  # Begin L10N call
        \s*                    # optional whitespace
        (["'])                 # opening quote
        (.*?)                  # The "key" value we want to extract
        (?<!\\)\1              # matching close quote, not backslashed
        \s*                    # optional trailing whitespace
        \)""", re.DOTALL|re.VERBOSE)
    # Matches $L({key: "a blah string", value: "blah"})
    # independent of the order in which key & value appear.
    key_val_regexp = re.compile(r"""
        \$L\(\{                # Begin L10N call, wrapped in curlies
        .*?                    # optional junk (like a "value:" bit)
        key:\s*                # "key:" bit
        (["'])                 # opening quote
        (.*?)                  # The "key" value we want to extract
        (?<!\\)\1              # matching close quote, not backslashed
        .*?                    # optional trailing junk (like a "value:" bit)
        \}\)""", re.DOTALL|re.VERBOSE)
    
    for relative_path, full_path in files:
        log("Processing %s" % relative_path)
        fid = codecs.open(full_path, "r", "utf-8")

        # Read the complete file
        fid.seek(0)
        data = fid.read()
        
        # Now find all $L constructs and tag with the relative path
        for matches in key_val_regexp.findall(data):
            key = matches[1].strip()
            lang_dict.setdefault(key, {})[relative_path] = 1
        for matches in simple_string_regexp.findall(data):
            key = matches[1].strip()
            lang_dict.setdefault(key, {})[relative_path] = 1

    return lang_dict


def read_strings(lang_file):
    """ Read any translations from strings.json. """
    log("Reading existing file '%s'" % lang_file)
    if not os.path.exists(lang_file):
        return {}
        
    fid = codecs.open(lang_file, "r", "utf-8")
    lang_data = json.load(fid)
    return lang_data


def read_lang(lang_file):
    """ Read existing lexicon data for a language, and reformat to the internal
    format.
    
    File is in the form:
    {
     "foo.js, bar.js, baz.js": {
      "ok": "",
      "cancel": ""
     },
     "foo.js": {
      "a string": "",
      "your mama", ""
     }
    }
    
    Returns:
    {key: {'files': {fname1: 1, fname2: 1}, 'value': "translation"},
     key2: {'files': {fname1: 1,...}
    """
    log("Reading existing file '%s'" % lang_file)
    if not os.path.exists(lang_file):
        return {}
        
    fid = codecs.open(lang_file, "r", "utf-8")
    lang_data = json.load(fid)
    
    lexicon = {}
    for flist, map in lang_data.iteritems():
        fnames = re.split(r",\s*", flist)
        for key, val in map.iteritems():
            if not val.strip():
                # Ignore untranslated values
                continue
            if key in lexicon:
                # The lexicon file should be denormalized.  If we find a key
                # in multiple places, it's an error.
                # FIXME better error message
                print >>sys.stderr, 'Multiple translations for key "%s", please fix' % key 
            else:
                lexicon[key] = {'value': val,
                                'files': dict([(f, 1) for f in fnames])}
    return lexicon


def merge_data(old_lang, old_strings, new_lang):
    """ Iterate through existing translated values, keeping all that still have
    keys in the code.   Returns a dict for the translators with keys separated
    by file, and a dict for strings.json containing translated values and no
    empty strings. 
    """
    log("Merging...")
    intermediate = {}
    
    # We'll build a version of strings.json, but it will only have 
    strings = {}
    
    # First see if there's a translation in strings.json, in case we're working
    # with an app that hasn't used pypalm for localization yet
    for k, v in old_strings.iteritems():
        if k in new_lang and v:
            # Keep only translated strings that still exist in the code
            intermediate[k] = {'value': v, 'files': new_lang[k]}
            # Put it in strings.json
            strings[k] = v
    
    # Look thru existing lexicon translations and keep the ones that still
    # have keys in the code.  These values are used in preference to data in
    # strings.json.  Note that when we read lexicon.json from disk we discard
    # untranslated keys.
    for k, v in old_lang.iteritems():
        if k in new_lang:
            # We have an existing translation value for this key.  Use the
            # translation, and assign it to the current list of files 
            intermediate[k] = {'value': v['value'],
                         'files': new_lang[k]}
            # Put it in strings.json
            strings[k] = v['value']

    # Add all new strings to the list.  They'll have empty translations, but
    # correct file listings.
    for k, v in new_lang.iteritems():
        if k not in intermediate:
            intermediate[k] = {'value': "",
                         'files': v}

    # Now twist the intermediate dict around to the on-disk lexicon format
    lexicon = {}
    for k, v in intermediate.iteritems():
        fspec = ", ".join(v['files'].keys())
        lexicon.setdefault(fspec, {})[k] = v['value']
    
    return lexicon, strings


def supported_langs(current_dir):
    """ Retrieves the supported langauges from framework_config.json """
    
    if not os.path.exists(os.path.join(current_dir, "framework_config.json")):
        return []
    
    framework_config = json.load(open(os.path.join(current_dir, "framework_config.json")))
    
    # Check for langs array
    if framework_config.has_key("languages"):
        return framework_config["languages"]


def create_language_directories(current_dir, lang):
    """ Create the required directories if necessary"""
    log("Creating directories for language '%s'" % lang)
    if not os.path.exists(os.path.join(current_dir, "resources")):
        os.mkdir(os.path.join(current_dir, "resources"))

    if not os.path.exists(os.path.join(current_dir, "resources", lang)):
        os.makedirs(os.path.join(current_dir, "resources", lang))


def save_language(current_dir, lang, lexicon, strings):
    """ Save lexicon.json for translators and strings.json for webOS. """
    log("Saving data for language '%s'" % lang)
    # Write the lexicon
    fid = open(os.path.join(current_dir, "resources", lang, "lexicon.json"), "w")
    json.dump(lexicon, fid, sort_keys=True, indent=1)
    fid.close()
    fid = open(os.path.join(current_dir, "resources", lang, "strings.json"), "w")
    json.dump(strings, fid, sort_keys=True, indent=0)
    fid.close()


def log(message):
    if not QUIET:
        print message
        

def localize(current_dir, quiet=True):
    """ This is the main function called from the module to
    localize the application"""
    QUIET = quiet
    log("Starting localization")
    # First check which languages we should support
    languages = supported_langs(current_dir)

    # Find all source files that might contain localizable strings
    files = get_files(current_dir)

    # Harvest strings from javascript
    lexicon = process_js_files(files)

    # For all supported langauges we need
    # to read the contents merge the contents and write them again
    for lang in languages:

        l_data = read_lang(os.path.join(current_dir, "resources",
                                        lang, "lexicon.json"))
        strings = read_strings(os.path.join(current_dir, "resources",
                                            lang, "strings.json"))
        merged_lexicon, merged_strings = merge_data(l_data, strings, lexicon)

        # Create dirs
        create_language_directories(current_dir, lang)

        # Write the lexicon.json and strings.json files
        save_language(current_dir, lang, merged_lexicon, merged_strings)
        if not quiet:
            print "Updated %s" % lang
