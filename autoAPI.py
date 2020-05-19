import urllib.request, xmltodict, json, collections
from collections import abc, OrderedDict
from flask import Flask, render_template, Markup, request, jsonify, redirect, url_for
import sqlite3

app = Flask(__name__)

''' ----------------- parseChildren() -------------------
    level - the current depth (root node is level 1)
    k, v - the key and value of the current node
    parent - the path to the parent of this node
    ------
    Add current node to the database and recursively call 
    for each of the children of this node
    -----------------------------------------------------
'''    
def parseChildren(level, k, v, parent):
    url = request.query_string.decode('UTF-8')
    collectionSize = len(v) if isinstance(v, list) else 0 # is this node a collection (list)?   
    newNode = parent + str(k) # generate the path to this node

    # prepare database and check for existing node
    db = sqlite3.connect('autoAPI.db')
    cursor = db.cursor()
    cursor.execute("select * from nodes where path = ? and url = ?", (newNode, url))
    dbRow = cursor.fetchone()
    nameChanged = 0
    if dbRow is None: # new node so add it to the database
        # first, get a unique name for the field
        name, stem, nameFound = str(k), parent[:-1], False
        while not nameFound:
            cursor.execute("select * from nodes where name = ? and url = ?", (name, url))
            if cursor.fetchone() is not None:
                name = stem[stem.rfind('/') + 1 :] + '/' + name
                stem = stem[: stem.rfind('/')][:-1]
                nameChanged = 1
            else:
                nameFound = True

        existingValue = ''
        cursor.execute("insert into nodes (url, path, value, everPresent, collection, leafNode, count, selected, parent, name, nameChanged) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                       (url, newNode, existingValue, 1, collectionSize, 0, 1, 1, parent[:-1], name, nameChanged) )
        db.commit()
    else: # node already exists so update count and cumulative collection size
        cursor.execute("select count, collection, value from nodes where path = ? and url = ?", (newNode, url) )
        dbRow = cursor.fetchone()
        newCount = int(dbRow[0]) + 1
        newCollection = int(dbRow[1]) + collectionSize
        existingValue = str(dbRow[2])
        cursor.execute("update nodes set count = ?, collection = ? where path = ? and url = ?", (newCount, newCollection, newNode, url) )
        db.commit()        
    cursor.close()

    if isinstance(v, collections.OrderedDict): 
        for key, value in v.items(): # node is a dictionary, so parse each member
            parseChildren(level+1, key, value, newNode + "/")
    elif isinstance(v, list): # node is a list
        for i in range(0, len(v)): # so parse each element
            for key, value in v[i].items():
                parseChildren(level+1, key, value, newNode + "/")
    else: # not a dictionary or a collection, so node must be a leaf node
        cursor = db.cursor()
        v = str(v) if v is not None and len(str(v).strip()) > 0 else "" # get value or empty string
        newValue = existingValue if len(existingValue) > 0 else v # only update value if it is currently empty
        cursor.execute("update nodes set value = ?, leafNode = ? where path = ? and url = ?", (newValue, 1, newNode, url))
        db.commit()
        cursor.close()
    db.close()


''' ----------------- generateSequenceCodes() -------------------
    Generate codes in the form 1.0001.0002.0003 for each node
    1. is the root node
    1.0001. is the first child of the root node
    1.0001.0002 is the 2nd child of the first child of the root
    etc...
    -------------------------------------------------------------
'''
def generateSequenceCodes():
    url = request.query_string.decode('UTF-8')
    stack = [] # stack of nodes to be processed
    db = sqlite3.connect('autoAPI.db')
    cursor = db.cursor()
    cursor.execute("select path from nodes where parent = ? and url = ?", ('', url)) # fetch the root node
    stack.append([cursor.fetchone()[0], "1."]) # and seed the stack with it
    cursor.execute("update nodes set sequenceCode = ? where parent = ? and url = ?", ('1.', '', url))
    db.commit()
    while len(stack) > 0:
        # pop node from stack and retrieve all of its children
        parentDetails = stack.pop() 
        cursor.execute("select path from nodes where parent = ? and url = ?", (parentDetails[0], url))
        children = cursor.fetchall()
        for childNum in range(1, len(children)+1): # process each child in turn
            thisNode = children[childNum-1][0] # get the path to the node
            # construct this sequence code by adding this child number to the parent's code
            thisSequenceCode = parentDetails[1] + '{:04d}'.format(childNum) + "." 
            # push on to the stack and update the node's database entry
            stack.append([thisNode, thisSequenceCode]) 
            cursor.execute("update nodes set sequenceCode = ? where path = ? and url = ?", (thisSequenceCode, thisNode, url))
            db.commit()
    cursor.close()
    db.close()


''' --------------------- generateOutput() ----------------------
    Generate the nested list structure for injection into the 
    template and return the HTML code
    -------------------------------------------------------------
'''
def generateOutput():
    url = request.query_string.decode('UTF-8')
    db = sqlite3.connect('autoAPI.db')
    cursor = db.cursor()
    cursor.execute("select variableURL from variableURLs where url = ?", (url, ))
    dbRow = cursor.fetchone()
    if dbRow is not None:
        variableURL = dbRow[0]
        parameterStyle = "inline"
    else:
        variableURL = url
        parameterStyle = "none"

    html = "<form style='display:inline' method='POST' action='/refresh?" + url + "'><input class='btn btn-primary' type='submit' name='refresh' value='Refresh'></form> &nbsp; &nbsp;"
    html = html + "<form style='display:inline' method='POST' action='/api?" + url + "'><input class='btn btn-primary' type='submit' name='api' value='Call API'> &nbsp; &nbsp;"
    html = html + "      <input type='checkbox' name='eliminateNullValues' value='yes'> Eliminate NULL Values &nbsp; &nbsp;"
    html = html + "      <input type='checkbox' name='collapseJSONResult' value='yes'> Collapse JSON Result &nbsp; &nbsp;"
    html = html + "      <span style='display: " + parameterStyle + "'>Parameter value <input type='text' name='parameter' value=''></span></form> <hr>"
    html = html + "<form id='apiForm' method='POST' action='/?" + url + "'>" 
    html = html + "Parameterise: <input class='parameterBoxStyle' type=text name='parameter' value ='" + variableURL +"'>" 
    html = html + "<ul style='margin-top: 30px'>"
    currentLevel = 1

    # retrieve all nodes ordered by sequence code
    cursor.execute("select path, value, everPresent, collection, leafNode, sequenceCode, selected, name from nodes  where url = ? order by sequenceCode asc", (url, ))
    dbRows = cursor.fetchall()
    for thisRow in range(0, len(dbRows)): # loop for each node
        thisLevel = dbRows[thisRow][0].count('/') # level is the number of '/' characters
        if thisLevel > currentLevel: # go to next level in the tree
            for _ in range(currentLevel, thisLevel):
                html = html + "<ul>"
        if thisLevel < currentLevel: # go to previous level in the tree
            for _ in range(currentLevel, thisLevel, -1):
                html = html + "</ul>"
        currentLevel = thisLevel
        # generate the output
        valueStr = str(dbRows[thisRow][1])
        valueStr = " (" + valueStr + ")" if len(valueStr.strip()) > 0 else ""
        optionalFlag = " [+] " if dbRows[thisRow][2] == 0 else ""
        collectionFlag = " [*] " if dbRows[thisRow][3] > 0 else ""
        checkedStr = " checked " if dbRows[thisRow][6] == 1 else ""
        checkboxStyleStr = "class='groupCheckbox'" if dbRows[thisRow][4] == 0 else "class='leafCheckbox'"  # reduced opacity for non-leaf checkboxes
        checkboxStr = "<input " + checkboxStyleStr + " type='checkbox' name='" + dbRows[thisRow][5] + "' " + checkedStr + "> " # if dbRows[thisRow][4] == 1 else ""
        inputBoxStr = "<input class='inputBoxStyle' type='text' name='name_" + dbRows[thisRow][5] + "' value='" + dbRows[thisRow][7] + "'> "
        styleStr = "groupNode" if dbRows[thisRow][4] == 0 else "leafNode"
        html = html + "<li class='small " + styleStr + "'>" + checkboxStr + inputBoxStr + dbRows[thisRow][0] + collectionFlag + optionalFlag + valueStr + "</li>"
    # all nodes processed, so add submit button and close the form and outer list structure    
    for _ in range(currentLevel, 1, -1):
        html = html + "</ul>"
    html = html + "<input type='submit' id='submit' class='displayed btn btn-primary' name='submit' value='Submit'></form>"
    html = html + "<h4 id='warning' class='notDisplayed'>Repeated element names as highlighted.  Please resolve before continuing.</h4>"
    cursor.close()
    db.close()
    return html


''' --------- Dictionary and List manipulation routines ---------
    updateList() - iterate across child lists
    updateDictionary() -
       if renameOrDelete is 'rename', 
          replace all keys in dict matching keysToCheck
       if renameOrDelete is 'delete',
          remove all keys in dict that are present in keysToCheck
    minimiseDictionary() - recursively remove all empty elements in dict 
    flattenDictionary() - collapse levels containing only a single element while preserving list structures
    -------------------------------------------------------------
'''
def updateList(l, parent, keysToCheck, renameOrDelete):
    for entry in l:
        if isinstance(entry, list):
            updateDictionary(entry, parent, keysToCheck, renameOrDelete)
        elif isinstance(entry, abc.Mapping):
            updateDictionary(entry, parent, keysToCheck, renameOrDelete)

def updateDictionary(dict, parent, keysToCheck, renameOrDelete):
    for key in list(dict.keys()):
        if renameOrDelete == 'delete' and key in keysToCheck:
            del(dict[key])
        if renameOrDelete == 'rename':
            thisKey = parent + '/' + key + '/'
            if thisKey in keysToCheck:
                dict[keysToCheck[thisKey]] = dict[key]
                del(dict[key])
                for keyCheck in list(keysToCheck.keys()):
                    startPos = keyCheck.find(thisKey)
                    if startPos == 0 and keyCheck != thisKey:
                        newValue = thisKey[:thisKey[:-1].rfind('/')] + '/' + keysToCheck[thisKey] + keyCheck[len(thisKey)-1:]
                        keysToCheck[newValue] = keysToCheck[keyCheck]
    for key in list(dict.keys()):
        if isinstance(dict[key], abc.Mapping):
            updateDictionary(dict[key], parent + '/' + key, keysToCheck, renameOrDelete)
        elif isinstance(dict[key], list):
            updateList(dict[key], parent + '/' + key, keysToCheck, renameOrDelete)
            
def minimiseDictionary(dictionary, eliminateNulls):

    def valueWanted(k, v, eliminateNulls):
        url = request.query_string.decode('UTF-8')
        db = sqlite3.connect('autoAPI.db')
        cursor = db.cursor()
        cursor.execute("select selected from nodes where name = ? and url = ?", (k, url))
        selected = cursor.fetchone()[0]
        if eliminateNulls:
            return True if v is not None else False
        else:
            return True if v is not None or selected == 1 else False

    if not isinstance(dictionary, list) and not isinstance(dictionary, abc.Mapping):
        return dictionary
    if isinstance(dictionary, list):
        return [ value for value in (minimiseDictionary(value, eliminateNulls) for value in dictionary) if value ] 
    return { key: value for key, value in ((key, minimiseDictionary(value, eliminateNulls)) for key, value in dictionary.items()) if valueWanted(key, value, eliminateNulls) } 

def flattenDictionary(dictionary):
    result = {}

    def flatten(collection, name=''):
        if type(collection) is dict:
            for element in collection:
                flatten(collection[element], element)
        elif type(collection) is list:
            result[name] = []
            for element in collection:
                result[name].append(flattenDictionary(element))
        else:
            result[name] = collection

    flatten(dictionary)
    return result


''' ------------------------ index() -------------------------
    Service the GET / and POST / requests
    POST request invoked from 'Refresh' button, so clear existing contents for the URL
    Retrieve XML source, convert to Python dictionary and 
    populate database table
    ----------------------------------------------------------
'''
@app.route("/", methods=["GET"])
def index():
    #url = 'http://apis.opendatani.gov.uk/translink/3042AA.xml'
    url = request.query_string.decode('UTF-8')

    # retrieve the XML from the source
    response = urllib.request.urlopen(url) 
    xmlData = response.read().decode("utf-8") # decode to convert bytes to string
    # use xmltodict library to parse the XML to a Python dictionary
    jsonData = xmltodict.parse(xmlData)
    # parse JSON data and generate database table of nodes
    # initial value pased is the root node of the structure
    for key, value in jsonData.items():
        parseChildren(1, key, value, "/")

    # check for any optional fields by comparing the count with the maximum number of occurences
    db = sqlite3.connect('autoAPI.db')
    cursor = db.cursor()
    cursor.execute("select distinct parent from nodes where url = ?", (url, )) # retrieve set of unique parent nodes
    dbRows = cursor.fetchall()
    for dbRow in dbRows: # for each parent (node path is in dbRow[0])
        cursor2 = db.cursor()
        # clear everPresent flag for nodes with fewer occurences than the maximum (i.e. those not present in all instances)
        cursor2.execute("update nodes set everpresent = ? where parent = ? and count <  (select max(count) from nodes where parent = ? and url = ?)", 
                         (0, dbRow[0], dbRow[0], url))
        db.commit()
        cursor2.close()
    cursor.close()
    db.close()

    # all nodes found so generate sequence codes
    generateSequenceCodes()

    # generate HTML code and pass to the output template
    return render_template("index.html", html=Markup(generateOutput()))


''' ------------------------ refresh() --------------------------
    Service the GET /refresh request
    Delete current database contents and redirect to GET /
    -------------------------------------------------------------
'''
@app.route("/refresh", methods=["POST"])
def refresh():
    url = request.query_string.decode('UTF-8')
    print("The URL is " + url)
    db = sqlite3.connect('autoAPI.db')
    cursor = db.cursor()
    cursor.execute("delete from nodes where url = ?", (url, ))
    db.commit()
    cursor.close()    
    print("About to redirect to /?" + url)
    return redirect("/?" + url)  # loses querystring value



''' ------------------------ setValues() ------------------------
    Service the POST /setValues request
    Retrieve selected checkboxes from the POST object, 
    update the database and generate the new form
    -------------------------------------------------------------
'''
@app.route("/", methods=["POST"])
def setValues():
    url = request.query_string.decode('UTF-8')
    # prepare database and remove any existing selections
    db = sqlite3.connect('autoAPI.db')
    cursor = db.cursor()
    cursor.execute("update nodes set selected = ? where url = ?", (0, url) )
    db.commit()

    if len(request.form.get('parameter')) > 0: # is there a variable URL specified?
        cursor.execute("select * from variableURLs where url = ?", (url, ))
        dbRow = cursor.fetchone()
        if dbRow is None: # specify a new variable URL
            cursor.execute("insert into variableURLs values (?, ?)", (url, request.form.get('parameter')))
        else: # update an existing variable URL
            cursor.execute("update variableURLs set variableURL = ? where url = ?", (request.form.get('parameter'), url))
        db.commit()
    else: # delete any existing parameterisation
        cursor.execute("delete from variableURLs where url = ?", (url, ))
    
    # iterate across summitted elements
    for key, value in request.form.items():
        if key[:2] == "1.": # is the item one of the checkboxes?
            cursor.execute("update nodes set selected = ? where sequenceCode = ? and url = ?", (1, key, url) )
            db.commit()
        
        if key[:7] == "name_1.": # it the item one of the text fields
            cursor.execute("select name from nodes where sequenceCode = ? and url = ?", (key[5:], url ))
            dbRow = cursor.fetchone()
            if value != dbRow[0]: # only update if it is a new name
                cursor.execute("update nodes set name = ?, nameChanged = ? where sequenceCode = ? and url = ?", (value, 1, key[5:], url))
                db.commit()
        
    cursor.close()
    db.close()
    return render_template("index.html", html=Markup(generateOutput()))


''' --------------------------- api() ---------------------------
    Service the GET /api request
    Query XML data source and return a JSON structure that 
    contains only the values identified in the database table
    -------------------------------------------------------------
'''
@app.route("/api", methods=["POST"])
def api():
    url = request.query_string.decode('UTF-8')
    db = sqlite3.connect('autoAPI.db')
    cursor = db.cursor()

    cursor.execute("select variableURL from variableURLs where url = ?", (url,) )
    dbRow = cursor.fetchone()
    if dbRow is not None:
        variableURL = dbRow[0]
        urlToOpen = variableURL[:variableURL.find('<')] + request.form.get('parameter') + variableURL[variableURL.find('>')+1:]
    else:
        urlToOpen = url
    print("Opening " + urlToOpen)

    collapse = True if request.form.get('collapseJSONResult') == 'yes' else False
    eliminateNulls = True if request.form.get('eliminateNullValues') == 'yes' else False
    # retrieve the XML from the source
    response = urllib.request.urlopen(urlToOpen) 
    xmlData = response.read().decode("utf-8") # decode to convert bytes to string

    # use xmltodict library to parse the XML to a Python dictionary
    jsonData = xmltodict.parse(xmlData)

    # rename all nodes according to the 'name' field in the database
    toBeChanged = {}
    cursor.execute("select path, name from nodes where nameChanged = ? and url = ?", (1, url))
    dbRows = cursor.fetchall()
    for dbRow in dbRows:
        toBeChanged[dbRow[0] + '/'] = dbRow[1]
    updateDictionary(jsonData, '', toBeChanged, 'rename')
    
    #get the list of fields to remove and eliminate from the jsonData structure
    cursor.execute("select name from nodes where leafNode = ? and selected = ? and url = ?", (1, 0, url) )
    dbRows = cursor.fetchall()
    cursor.close()
    db.close()
    nodesToRemove = []
    for dbRow in dbRows:
        nodesToRemove.append(dbRow[0])
    updateDictionary(jsonData, '', nodesToRemove, 'delete')

    jsonData = minimiseDictionary(jsonData, eliminateNulls)    # delete all unwanted leaf nodes
    if collapse:
        jsonData = flattenDictionary(jsonData) # flatten the structure as far as possible
    return jsonify(jsonData)


# run the Flask application
if __name__ == "__main__":
    app.run(debug=True)