#!/usr/bin/env python

"""
Creates html reference documents for each Pmw megawidget, containing
title, image, name, inheritance, description, options, components,
aliases, methods and example code.

Markup conventions:
    'italic':   formal parameters, emphasis
    *bold*:     paragraph headers, class, option, component and
                component group names, literal text, constants, constant
                dictionary keys
    /code/:     methods, code fragments, unix commands, urls, file and
                directory names
"""

# Directory containing the Pmw library.
pmwLibDir = '../lib'
pmwPackageDir = '../../..'
pmwTextDir = 'text'
imageDir   = 'images'

import sys
sys.path[:0] = [pmwLibDir]
sys.path[:0] = [pmwPackageDir]

# The raw text is in this directory.
sys.path[:0] = [pmwTextDir]

import cgi
import dis
import html
import os
import re
import shutil
import string
import time
import types
import tkinter
import StructuredText
import Pmw

CO_VARARGS = 4
CO_VARKEYWORDS = 8

if len(sys.argv) != 1:
    print(sys.argv[0] + ' takes no arguments. Exiting.')
    sys.exit()

PMW_DIR = os.path.basename(os.path.dirname(os.getcwd()))[4:]
VERSION = re.sub('_', '.', PMW_DIR)
VERSION_DATE = time.strftime('%e %B %Y', time.localtime(time.time())).strip()
Pmw.setversion(VERSION)

# Create _modules and _functions attributes.
defFile = '../../Pmw_%s/lib/Pmw.def' % PMW_DIR
if not os.path.exists(defFile):
    print('No such file' + defFile)
    sys.exit()
exec(open(defFile).read())

# Where to put the html documents.
pmwDocHtmlDir = '../doc'
try:
    os.mkdir(pmwDocHtmlDir)
except os.error:
    pass
if pmwDocHtmlDir[-1] != '/':
    pmwDocHtmlDir = pmwDocHtmlDir + '/'

# ======================================================================
# Define pattern to find forwarded methods.

pattern = re.compile(
    '.*forwardmethods\('
    ' *'
    '(?P<fromClass>[^,]*)'
    ' *, *'
    '(?P<toClass>[^,]*)'
    ' *, *'
    "'(?P<toPart>[^']*)'"
    ' *\).*'
    '.*'
)

# ======================================================================
# Return all information about megawidget.

def extractWidgetInfo (fileName, widgetName):
    info = {}
    cls = getattr(Pmw, widgetName)

    # Create an instance of the megawidget with all optional
    # components.  Since the options to do this vary, try each of the
    # following until the megawidget is created.
    tryKeywords = (
        {'separatorwidth' : 1, 'iconpos' : 'w'},# AboutDialog, MessageDialog
        {'labelpos' : 'w', 'borderframe' : 1,   # ScrolledText, HistoryText
         'columnheader' : 1,
         'rowheader' : 1,
         'rowcolumnheader' : 1,
        },
        {'labelpos' : 'w', 'borderframe' : 1},  # ScrolledCanvas
        {'labelpos' : 'w'},                     # ButtonBox, ComboBox, Counter,
                                                # EntryField, OptionMenu,
                                                # LabeledWidget, MessageBar,
                                                # RadioSelect, ScrolledField,
                                                # ScrolledFrame,
                                                # ScrolledListBox, TimeCounter
        {'separatorwidth' : 1},                 # ComboBoxDialog, CounterDialog,
                                                # Dialog, PromptDialog,
                                                # SelectionDialog, TextDialog
        {},                                     # All other widgets
    )
    field = None
    for dict in tryKeywords:
        try:
            field = cls(*(), **dict)
            break
        except (KeyError, TypeError):
            pass
    if field is None:
        raise RuntimeError('Could not create instance of ' + str(cls))

    if widgetName in baseClassList:
        widgetgroup = 'Base classes'
    elif widgetName[-6:] == 'Dialog':
        widgetgroup = 'Dialogs'
    else:
        widgetgroup = None

    bases = []
    for base in cls.__bases__:
        if base.__name__ != 'object':
            bases.append(base.__name__)
            if widgetgroup is None and base in widgetBaseClasses:
                widgetgroup = 'Widgets'
    if widgetgroup is None:
        widgetgroup = 'Miscellaneous'

    components = []
    for name in field.components():
        component = field.component(name)
        group = field.componentgroup(name)
        components.append(
                (name, component, component.__class__.__name__, group))
    methods = []
    for name, value in cls.__dict__.items():
        if name[0] != '_' and type(value) == types.FunctionType:
            varnames = value.__code__.co_varnames
            # Don't list forwarded methods. (They can be found by their
            # unusual variable names.)
            if varnames != ('this', 'args', 'kw'):
                args = getFunctionArgs(value, 1)
                methods.append((name, args))

    methods.sort()

    forwardedcomponents = []
    for line in open(fileName).readlines():
        match = pattern.match(line)
        if match is not None:
            fromClass = match.group('fromClass')
            toClass = match.group('toClass')
            toPart = match.group('toPart')
            if widgetName == fromClass:
                toWidget = getattr(field, toPart)
                for name, megawidget, cls, group in components:
                    if megawidget == toWidget:
                        forwardedcomponents.append(name)
    # Do not sort forwardedcomponents (they are in search order).

    info['bases'] = bases
    info['options'] = field.options()
    info['components'] = components
    info['aliases'] = field.componentaliases()
    info['methods'] = methods
    info['forwardedcomponents'] = forwardedcomponents
    info['widgetgroup'] = widgetgroup

    try:
        text = __import__(widgetName + '_text')
    except ImportError:
        text = default_text

    for attr in ('name', 'reviewdate', 'description', 'no_auto_default',
            'text', 'sections'):
        if not hasattr(text, attr):
            setattr(text, attr, getattr(default_text, attr))

    for key in ('options', 'components', 'methods'):
        if not key in text.text:
            text.text[key] = default_text.text[key]

    info['text'] = text

    return info

# ======================================================================

def getFunctionArgs(function, isMethod = 0):
    # Form a string representation of all the arguments to
    # the function.

    code = function.__code__
    numargs = code.co_argcount
    defaults = function.__defaults__
    co_flags = code.co_flags
    varnames = code.co_varnames

    if defaults is None:
        normalArgs = numargs
    else:
        normalArgs = numargs - len(defaults)

    # First do the normal arguments.
    args = []
    p = 0
    if isMethod:
        startarg = 1
    else:
        startarg = 0
    for index in range(startarg, numargs):
        arg = varnames[index]

        # anonymous arguments
        c = code.co_code
        if not arg or arg[0] == ".":
            vars = []
            while p < len(c):
                v = ord(c[p])
                if v >= dis.HAVE_ARGUMENT:
                    s, v = dis.opname[v], ord(c[p+1]) + ord(c[p+2])*256
                    p = p + 3
                    if s == "UNPACK_TUPLE":
                        count = v
                    elif s == "STORE_FAST":
                        vars.append(varnames[v])
                        if len(vars) >= count:
                            break
                else:
                    p = p + 1
            if vars:
                arg = "(" + ", ".join(vars) + ")"



        arg = '<em>' + arg + '</em>'
        if index >= normalArgs:
            arg = arg + ' = <strong>' + \
                    getRepr(defaults[index - normalArgs]) + '</strong>'
        args.append(arg)

    # Now add the varargs argument, eg '*args'.
    index = numargs
    if (co_flags & CO_VARARGS) != 0:
        arg = '*<em>' + varnames[index] + '</em>'
        args.append(arg)
        index = index + 1

    # Now add the keyword args argument, eg '**kw'.
    if (co_flags & CO_VARKEYWORDS) != 0:
        arg = '**<em>' + varnames[index] + '</em>'
        args.append(arg)
        index = index + 1

    return '(' + ', '.join(args) + ')'

def getRepr(obj):
    if obj is Pmw.DEFAULT:
        return 'Pmw.DEFAULT'
    if obj is Pmw.SELECT:
        return 'Pmw.SELECT'
    if type(obj) == type(0.1):
        return str(obj)
    return repr(obj)

# ======================================================================

def getPartText(widgetName, part, type):
    # Find the description for the 'type' (options, components or
    # methods) named 'part' for the widget class named 'widgetName'.

    # First check if the widget-specific description contains the
    # part.
    textDict = widgetInfo[widgetName]['text'].text[type]
    if part in textDict:
        return textDict[part].strip()

    # No text was found specific to the widget, try the base class
    # descriptions.
    for base in widgetInfo[widgetName]['bases']:
        text = getPartText(base, part, type)
        if text is not None:
            return text.strip()

    # No text was found specific to the widget or base classes, try
    # the special createlabel descriptions.
    if type == 'options':
        if part == 'labelmargin':
            return default_text.labelmargin_option.strip()
        elif part == 'labelpos':
            return default_text.labelpos_option.strip()

    if type == 'components':
        if part == 'label':
            return default_text.label_component.strip()

    # No description found
    return None

# ======================================================================

class default_text:
    name = "..."
    description = "..."
    reviewdate = ""
    no_auto_default = ()
    text = {}
    text['options'] = {}
    text['components'] = {}
    text['methods'] = {}
    sections = ()

    labelmargin_option = """
        If the *labelpos* option is not *None*, this specifies the
        distance between the *label* component and the rest of the
        megawidget.

    """

    labelpos_option = """
        Specifies where to place the *label* component.  If not
        *None*, it should be a concatenation of one or two of the
        letters *'n'*, *'s'*, *'e'* and *'w'*.  The first letter
        specifies on which side of the megawidget to place the label. 
        If a second letter is specified, it indicates where on that
        side to place the label.  For example, if *labelpos* is *'w'*,
        the label is placed in the center of the left hand side; if
        it is *'wn'*, the label is placed at the top of the left
        hand side; if it is *'ws'*, the label is placed at the
        bottom of the left hand side.

        If *None*, a label component is not created.

    """

    label_component = """
        If the *labelpos* option is not *None*, this component is
        created as a text label for the megawidget.  See the
        *labelpos* option for details.  Note that to set, for example,
        the *text* option of the label, you need to use the *label_text*
        component option.

    """

# ======================================================================
# Define header and trailer for html document.

def header(title = None, heading = None):
    headerStr = """
    <html>
    <head>
    <meta name="description" content="Pmw - a toolkit for building high-level compound widgets in Python">
    <meta name="content" content="python, megawidget, mega widget, compound widget, gui, tkinter">
    <title>%(title)s</title>
    </head>

    <body bgcolor="#ffffff" text="#000000" link="#0000ee"
        vlink="551a8b" alink="ff0000">

    <h1 ALIGN="CENTER">%(heading)s</h1>
    """

    return headerStr % locals()

dateString = time.strftime('%e %b %Y', time.localtime(time.time()))
def trailer(noBack = 0, extra = ''):
    if noBack:
        back = ''
    else:
        back = ' - <a href="index.html">Home</a>'
    trailerStr = """
    <font size=-1>
    <center><P ALIGN="CENTER">
    Pmw %(version)s -
    %(date)s
    %(back)s
    %(extra)s
    </p></center>
    </font>

    </body>
    </html>
    """ % {'back': back,'version': VERSION, 'date': dateString, 'extra' : extra}

    return trailerStr

def blue_line():
    lineStr = """
    <center><P ALIGN="CENTER">
    <IMG SRC = blue_line.gif ALT = "" WIDTH=320 HEIGHT=5>
    </p></center>
    """

    return lineStr

# ======================================================================
# Now that all the information has been extracted, print html document.

def link(name, target=None, style='html'):
    if name in widgetInfo:
        if target is None:
            if style == 'html':
                return '<a href="' + name + '.html">Pmw.' + name + '</a>'
            else:
                return '~' + name + '~'
        else:
            if style == 'html':
                return '<a href="' + name + '.html#' + target + '">Pmw.' + name + '</a>'
            else:
                return '~' + name + '#' + target + '~'
    else:
        return 'tkinter.' + name

# ======================================================================

def printSection(widgetName, sectionName):
    global sectionsUsed

    info = widgetInfo[widgetName]
    fullWidgetName = 'Pmw.' + widgetName

    for name, after, relative, text in info['text'].sections:
        if not after and relative == sectionName:
            sectionsUsed = sectionsUsed + 1
            print('<dt> <h3>' + name + '</h3></dt><dd>')
            print(StructuredText.gethtml(text))
            print('</dd>')

    if sectionName == 'Name':
        print('<dt> <h3>Name</h3></dt><dd>')
        text = fullWidgetName + '() - ' + info['text'].name
        print(StructuredText.gethtml(text))
        print('</dd>')

    elif sectionName == 'Inherits':
        if len(info['bases']) > 0:
            print('<dt> <h3>Inherits</h3></dt><dd>')
            for base in info['bases']:
                print(link(base) + '<br>')
            print('</dd>')

    elif sectionName == 'Description':
        print('<dt> <h3>Description</h3></dt><dd>')
        text = info['text'].description
        print(StructuredText.gethtml(text))
        print('</dd>')

    elif sectionName == 'Options':
        if len(info['options']) > 0:
            print('<dt> <h3>Options</h3></dt><dd>')
            print('Options for this megawidget and its base')
            print('classes are described below.<p></p>')
            options_with_text = list(info['text'].text['options'].keys())
            for option, default, isinit in info['options']:
                print('<a name=option.' + option + '></a>')
                print('<dl><dt> <strong>' + option)
                print('</strong></dt><dd>')
                text = ''
                if isinit:
                    text = 'Initialisation option. '
                else:
                    text = ''
                optionText = getPartText(widgetName, option, 'options')
                if optionText is None:
                    sys.stderr.write('ERROR: no text for ' + widgetName +
                        ' option ' + option + '\n')
                else:
                    text = text + optionText
                if option in info['text'].text['options']:
                    options_with_text.remove(option)
                if option not in info['text'].no_auto_default:
                    if type(default) == type(()) and len(default) > 0:
                        text = text + ' The default is *('
                        for s in default:
                            text = text + "\\'" + default[0] + "\\', "
                        if len(default) == 1:
                            text = text[:-1]
                        else:
                            text = text[:-2]
                        text = text + ")*."
                    else:
                        text = text + ' The default is *' + getRepr(default) + '*.'
                text = StructuredText.gethtml(text)
                if text[:3] == '<p>':
                    print(text[3:])
                else:
                    print(text)
                print('</dd></dl>')
            print('</dd>')

            if len(options_with_text) > 0:
                sys.stderr.write('ERROR: unknown options ' +
                        str(options_with_text) + ' for ' + fullWidgetName + '\n')

    elif sectionName == 'Components':
        global componentClass
        componentClass = {}
        if len(info['components']) > 0:
            print('<dt> <h3>Components</h3></dt><dd>')
            print('Components created by this megawidget and its base')
            print('classes are described below.<p></p>')
            components_with_text = list(info['text'].text['components'].keys())
            for component, megawidget, cls, group in info['components']:
                componentClass[component] = cls
                print('<a name=component.' + component + '></a>')
                print('<dl><dt> <strong>' + component)
                print('</strong></dt><dd>')
                componentText = getPartText(widgetName, component, 'components')
                if componentText is None:
                    sys.stderr.write('ERROR: no text for ' + widgetName +
                        ' component ' + component + '\n')
                    text = ''
                else:
                    text = componentText
                if component in info['text'].text['components']:
                    components_with_text.remove(component)
                text = text + ' By default, this component is a ' + \
                        link(cls, style = 'structured') + '.'
                if group is not None:
                    text = text + ' Its component group is *' + group + '*.'
                text = StructuredText.gethtml(text)
                if text[:3] == '<p>':
                    print(text[3:])
                else:
                    print(text)
                print('</dd></dl>')
            print('</dd>')

            if len(components_with_text) > 0:
                sys.stderr.write('ERROR: unknown components ' +
                        str(components_with_text) + ' for ' + fullWidgetName + '\n')

    elif sectionName == 'Component aliases':
        if len(info['aliases']) > 0:
            print('<dt> <h3>Component aliases</h3></dt><dd>')
            print('Sub-components of components of this megawidget')
            print('may be accessed via the following aliases.<p></p>')
            for alias, name in info['aliases']:
                print('<dl><dt> <strong>' + alias)
                print('</strong></dt><dd>')
                print('Alias for <strong>' + name + '</strong>.')
                print('</dd></dl>')
            print('</dd>')

    elif sectionName == 'Methods':
        print('<a name=methods></a>')
        print('<dt> <h3>Methods</h3></dt><dd>')
        bases = info['bases']
        if len(bases) > 0:
            if len(info['methods']) == 0:
                print('This megawidget has no methods of its own.')
            else:
                print('Only methods specific to this megawidget are described below.')
            print('For a description of its inherited methods, see the')
            if len(bases) == 1:
                base = bases[0]
                print('manual for its base class')
                print('<strong>' + link(base, 'methods') + '</strong>.')
            else:
                print('manuals for its base classes ')
                linkText = '<strong>' + link(base, 'methods') + '</strong>.'
                for i in len(bases):
                    base = bases[i]
                    if i == len(bases) - 1:
                        print(linkText + '.')
                    elif i == len(bases) - 2:
                        print(linkText + ' and ')
                    else:
                        print(linkText + ', ')

            if len(info['forwardedcomponents']) > 0:
                if len(info['forwardedcomponents']) == 1:
                    cls = componentClass[info['forwardedcomponents'][0]]
                    component = info['forwardedcomponents'][0]
                    print('In addition, methods from the')
                    print('<strong>' + link(cls, 'methods') + '</strong> class')
                    print('are forwarded by this megawidget to the')
                    print('<strong>' + component + '</strong> component.')
                else:
                    print('In addition, methods from the following classes')
                    print('are forwarded by this megawidget.')
                    for component in info['forwardedcomponents']:
                        cls = componentClass[component]
                        print('Methods from <strong>' + link(cls, 'methods') + '</strong>')
                        print('are forwarded to the')
                        print('<strong>' + component + '</strong> component.')
                    print('Forwarded methods are searched in the order given.')

            print('<p></p>')

        methods_with_text = list(info['text'].text['methods'].keys())
        for method, args in info['methods']:
            if method == 'destroy' and \
                    widgetName not in ('MegaToplevel', 'MegaArchetype'):
                # Many widgets need to override destroy() just to unset timers.
                continue
            print('<a name=method.' + method + '></a>')
            print('<dl><dt> <strong>' + method + '</strong>' + args + '</dt><dd>')
            text = getPartText(widgetName, method, 'methods')
            if text is None:
                sys.stderr.write('ERROR: no text for ' + widgetName +
                    ' method ' + method + '\n')
                print('<p></p>')
            else:
                text = StructuredText.gethtml(text)
                if text[:3] == '<p>':
                    print(text[3:])
                else:
                    print(text)
            if method in info['text'].text['methods']:
                methods_with_text.remove(method)
            print('</dd></dl>')
        print('</dd>')

        if len(methods_with_text) > 0:
            sys.stderr.write('ERROR: unknown methods ' +
                    str(methods_with_text) + ' for ' + fullWidgetName + '\n')

    elif sectionName == 'Example':
        demoFile = '../demos/' + widgetName + '.py'
        if os.path.isfile(demoFile):
            print('<dt> <h3>Example</h3></dt><dd>')
            if gotImage:
                print('The image at the top of this manual is a snapshot')
                print('of the window (or part of the window) produced')
                print('by the following code.<p></p>')
            else:
                print('Example code using %s.<p></p>' % fullWidgetName)
            lines = []
            for line in open(demoFile).readlines():
                if len(lines) != 0:
                    if line == ('#' * 70) + '\n':
                        # End of Demo class
                        break
                    else:
                        lines.append(line)
                if line == 'class Demo:\n':
                    lines.append(line)

            while lines[-1] == '\n':
                del lines[-1]
            print('<pre>')
            escapedText = html.escape(''.join(lines))
            escapedText = re.sub('&#x27;', "'", escapedText)
            print(StructuredText.untabify(escapedText))
            print('</pre>')
            print('</dd>')
        else:
            if widgetName not in baseClassList:
                sys.stderr.write('ERROR: no %s demo for %s\n' %
                    (demoFile, fullWidgetName))

    for name, after, relative, text in info['text'].sections:
        if after and relative == sectionName:
            sectionsUsed = sectionsUsed + 1
            print('<dt> <h3>' + name + '</h3></dt><dd>')
            print(StructuredText.gethtml(text))
            print('</dd>')

def create_index_file():
    sys.stdout = open(pmwDocHtmlDir + 'refindex.html', 'w')
    print(header(
        title = 'Pmw reference manual index',
        heading = 'Pmw reference manual<br>index'
    ))
    print(blue_line())

    # Print the contents in this order, adding any other megawidget groups after.
    groups = ['Base classes', 'Widgets', 'Dialogs', 'Miscellaneous']
    for widgetName in megawidgets:
        info = widgetInfo[widgetName]
        if info['widgetgroup'] not in groups:
            groups.append(info['widgetgroup'])

    for group in groups:
        print('<dl><dt> <strong>' + group + '</strong></dt><dd>')
        if group == 'Base classes':
            orderedlist = baseClassList
        else:
            orderedlist = megawidgets
        for widgetName in orderedlist:
            info = widgetInfo[widgetName]
            if info['widgetgroup'] == group:
                if hasattr(info['text'], 'complete'):
                    icon = 'blueball.gif'
                else:
                    icon = 'halfblueball.gif'
                print('<IMG SRC = ' + icon + ' ALT = "" WIDTH=14 HEIGHT=14>' + link(widgetName))
                # if group == 'Miscellaneous':
                    # print('<br>')
        if group == 'Miscellaneous':
            modules = list(_modules)
            modules.sort()
            for module in modules:
                print('<IMG SRC = blueball.gif ALT = "" WIDTH=14 HEIGHT=14>' + '<a href="' + module + '.html">Pmw.' + module + '</a>')
                # print('<br>')
            print('<IMG SRC = blueball.gif ALT = "" WIDTH=14 HEIGHT=14><a href="PmwFunctions.html">Module functions</a>')
            # print('<br>')
        print('</dd></dl>')

    # print('Documentation key:')
    # print('<IMG SRC = blueball.gif ALT = "" WIDTH=14 HEIGHT=14> = complete,')
    # print('<IMG SRC = halfblueball.gif ALT = "" WIDTH=14 HEIGHT=14> = some descriptions missing')
    print(blue_line())
    print(trailer())

# ======================================================================

def getWidgetInfo():
    widgetInfo = {}
    files = os.listdir(pmwLibDir)
    files.sort()
    for file in files:
        if file[:3] == 'Pmw' and file[-3:] == '.py':
            fileName = pmwLibDir + '/' + file
            moduleName = file[:-3]
            module = __import__(moduleName)
            widgetNames = ()
            if moduleName == 'PmwBase':
                widgetNames = ('MegaArchetype', 'MegaToplevel', 'MegaWidget')
            else:
                widgetName = moduleName[3:]
                if hasattr(module, widgetName):
                    widgetNames = (widgetName,)
            for widgetName in widgetNames:
                widgetInfo[widgetName] = extractWidgetInfo(fileName, widgetName)
    return widgetInfo

# ======================================================================

def create_widget_manuals():
    global sectionsUsed
    global gotImage
    for widgetName in megawidgets:
        info = widgetInfo[widgetName]
        sys.stdout = open(pmwDocHtmlDir + widgetName + '.html', 'w')
        fullWidgetName = 'Pmw.' + widgetName
        print(header(title = fullWidgetName + ' reference manual', heading = fullWidgetName))

        fileName = widgetName + '.gif'
        path = os.path.join(imageDir, fileName)
        gotImage = os.path.isfile(path)
        if gotImage:
            image = tkinter.PhotoImage(file = path)
            print('<center><IMG SRC=%s ALT="" WIDTH=%s HEIGHT=%s></center>' % (fileName, image.width(), image.height()))
        else:
            if widgetName not in baseClassList:
                sys.stderr.write('ERROR: no %s image for %s\n' %
                    (path, fullWidgetName))

        sectionsUsed = 0
        print('<dl>')
        printSection(widgetName, 'Name')
        printSection(widgetName, 'Inherits')
        printSection(widgetName, 'Description')
        printSection(widgetName, 'Options')
        printSection(widgetName, 'Components')
        printSection(widgetName, 'Component aliases')
        printSection(widgetName, 'Methods')
        printSection(widgetName, 'Example')
        print('</dl>')

        if len(info['text'].sections) != sectionsUsed:
            sys.stderr.write('ERROR: unused sections for' + fullWidgetName + '\n')

        print(blue_line())
        if info['text'].reviewdate != '':
            extra = '<br>Manual page last reviewed: ' + info['text'].reviewdate
        else:
            extra = ''
        print(trailer(extra = extra))

# ======================================================================

def create_function_manual():
    sys.stdout = open(pmwDocHtmlDir + 'PmwFunctions.html', 'w')
    print(header(
        title = 'Pmw functions reference manual',
        heading = 'Pmw functions',
    ))
    functionNames = []
    import PmwBase
    for name, value in PmwBase.__dict__.items():
        if name[0] != '_' and type(value) == types.FunctionType:
            args = getFunctionArgs(value)
            functionNames.append((name, args))
    for name in list(_functions.keys()):
        value = getattr(Pmw, name)
        if hasattr(value, '__code__'):
            args = getFunctionArgs(value)
            functionNames.append((name, args))
        elif name not in ('OK', 'ERROR', 'PARTIAL'):
            sys.stderr.write('ERROR: ' + name + ' is not a function\n')

    import PmwLoader
    cls = PmwLoader.PmwLoader
    for name, value in cls.__dict__.items():
        if name[0] != '_' and type(value) == types.FunctionType:
            args = getFunctionArgs(value, 1)
            functionNames.append((name, args))
    functionNames.sort()

    import PmwFunctions_text
    print('<dl>')
    for name, args in functionNames:
        print('<dt> <strong>Pmw.' + name + '</strong>' + args + '</dt><dd>')
        if hasattr(PmwFunctions_text, name):
            text = getattr(PmwFunctions_text, name)
            text = StructuredText.gethtml(text)
            print(text)
        else:
            sys.stderr.write('ERROR: no text for function ' + name + '\n')
            print('<p></p>')
        print('</dd>')
    print('</dl>')

    print(blue_line())
    print(trailer())

# ======================================================================

def create_module_manual(moduleName):
    sys.stdout = open(pmwDocHtmlDir + moduleName + '.html', 'w')
    print(header(
        title = 'Pmw.' + moduleName + ' reference manual',
        heading = 'Pmw.' + moduleName
    ))

    print('<dl>')
    textModule = __import__(moduleName + '_text')
    print('<dt> <h3>Name</h3></dt><dd>')
    text = 'Pmw.' + moduleName + ' - ' + textModule.name
    print(StructuredText.gethtml(text))
    print('</dd>')
    print('<dt> <h3>Description</h3></dt><dd>')
    text = textModule.description
    print(StructuredText.gethtml(text))
    print('</dd>')

    functionNames = []
    module = __import__('Pmw' + moduleName)
    for name, value in module.__dict__.items():
        if name[0] != '_' and type(value) == types.FunctionType:
            functionNames.append((name, value))
    functionNames.sort()

    print('<dt> <h3>Functions</h3></dt><dd>')
    print('The following functions are available.<p></p>')
    functions_with_text = list(textModule.text['functions'].keys())

    print('<dl>')
    for name, function in functionNames:
        args = getFunctionArgs(function)
        print('<dt> <strong>Pmw.' + moduleName + '.' + name + '</strong>' + args + '</dt><dd>')
        if name in textModule.text['functions']:
            text = textModule.text['functions'][name]
            text = StructuredText.gethtml(text)
            if text[:3] == '<p>':
                print(text[3:])
            else:
                print(text)
            functions_with_text.remove(name)
        else:
            sys.stderr.write('ERROR: no text for function ' + name + '\n')
            print('<p></p>')
        print('</dd>')
    print('</dl>')
    print('</dd></dl>')

    if len(functions_with_text) > 0:
        sys.stderr.write('ERROR: unknown functions ' +
                str(functions_with_text) + ' for module' + moduleName + '\n')

    print(blue_line())
    if textModule.reviewdate != '':
        extra = '<br>Manual page last reviewed: ' + textModule.reviewdate
    else:
        extra = ''
    print(trailer(extra = extra))

# ======================================================================

def create_page(moduleName, pageName, title):
    sys.stdout = open(pmwDocHtmlDir + pageName, 'w')
    print(header(title = title, heading = title))
    module = __import__(moduleName)
    text = StructuredText.gethtml(module.text)
    print(text)
    print(blue_line())
    print(trailer())

# ======================================================================

def copy_page(sourceName, pageName, title, heading = None, noBack = 0):
    if heading is None:
        heading = title
    sys.stdout = open(pmwDocHtmlDir + pageName, 'w')
    print(header(title = title, heading = heading))
    text = open(os.path.join(pmwTextDir,sourceName)).read()
    text = re.sub('PMW_VERSION', VERSION, text)
    text = re.sub('PMW_DIR', PMW_DIR, text)
    text = re.sub('VERSION_DATE', VERSION_DATE, text)
    print(text)
    print(blue_line())
    print(trailer(noBack = noBack))

# ======================================================================

def copy_images():
    files = os.listdir(imageDir)
    for file in files:
        if file[-4:] == '.gif':
            shutil.copy(os.path.join(imageDir,file), pmwDocHtmlDir)

# ======================================================================

def copy_file(fileName):
    shutil.copy(os.path.join(pmwTextDir,fileName), pmwDocHtmlDir)

# ======================================================================

baseClassList = ('MegaArchetype', 'MegaWidget', 'MegaToplevel')
widgetBaseClasses = (Pmw.MegaWidget, Pmw.MegaArchetype, Pmw.ScrolledText)

root = Pmw.initialise()

widgetInfo = getWidgetInfo()
megawidgets = list(widgetInfo.keys())
megawidgets.sort()

create_index_file()
create_widget_manuals()
create_function_manual()

for moduleName in _modules:
    create_module_manual(moduleName)

create_page('features_text', 'features.html', 'Pmw features')
create_page('changes_text', 'changes.html', 'Changes to Pmw')
create_page('todo_text', 'todo.html', 'Pmw todo list')
create_page('bugs_text', 'bugs.html', 'List of known bugs')
create_page('copyright_text', 'copyright.html', 'Pmw copyright')
copy_page('index_text.html', 'index.html', 'Pmw megawidgets ' + VERSION,
        'Pmw ' + VERSION, noBack = 1)
copy_page('starting_text.html', 'starting.html', 'Getting started with Pmw')
copy_page('demosandtests_text.html', 'demosandtests.html', 'Pmw demonstrations and tests')
copy_page('howtobuild_text.html', 'howtobuild.html',
        'How to build Pmw megawidgets')
create_page('dynamicloader_text', 'dynamicloader.html', 'Dynamic loader')
create_page('porting_text', 'porting.html',
        'Porting between different versions of Pmw')
copy_page('howtouse_text.html', 'howtouse.html', 'How to use Pmw megawidgets')
copy_images()
copy_file('example.py')
copy_file('exercises.py')
copy_file('../../demos/ExampleDemo.py')
copy_file('../../tests/ScrolledText_test.py')
