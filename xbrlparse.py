from collections import namedtuple
from xml.etree.cElementTree import parse
import pandas as pd

class XBRLParser:

    def __init__(self, instanceXML:str, file_htm: str, file_cal:str, file_def:str, file_lab:str) -> None:
        
        self.instanceXML = instanceXML
        self.file_htm = file_htm
        self.file_cal = file_cal
        self.file_def = file_def
        self.file_lab = file_lab
    
    
        # create a named tuples
        FilingTuple = namedtuple("FilingTuple", ['file_path', 'namespace_element', 'namespace_label'])

        self.files_list = [
            FilingTuple(file_cal, r'{http://www.xbrl.org/2003/linkbase}calculationLink', 'calculation'),
            FilingTuple(file_def, r'{http://www.xbrl.org/2003/linkbase}definitionLink', 'definition'),
            FilingTuple(file_lab, r'{http://www.xbrl.org/2003/linkbase}labelLink', 'label')
            ]
        
        calculations, definitions, labels = self.parseAuxFiles()
        facts_nan, facts_num, contexts, units = self.parseMain()
        self.calculationsDF, self.definitionsDF, self.labelsDF, self.factsNan_DF, self.factsNum_DF, self.contextsDF, self.unitsDF = self.createDataFrames(calculations, definitions, labels, 
                                                                                                      facts_nan, facts_num, contexts, units)
    
    
    '''PARSE THE AUXILIARY  XBRL FILES (_CAL.XML, _DEF.XML, _LAB.XML)'''

    def parseAuxFiles(self):

        # Define XBRL Data Storage
        calculations = [] # Parent, Children, Weight, Order
        definitions = [] # Line Items, Items, Table Items, Axes, Domains, Member
        labels = [] # Terse Label Text, Language Label Text, Documentation Label Text, Main Label

        # loop through _cal, _def, _lab files:
        for file in self.files_list:

            # parse the file
            tree = parse(file.file_path)

            # grab all the namespace elements in the tree
            elements = tree.findall(file.namespace_element)

            # If we are in _cal.xml
            if file.namespace_label == 'calculation':
                
                # Iterate through calculationLink
                for element in elements:

                    # Iterate through each Link, grab only calculationArc
                    for children in element.iter():

                        label = children.tag.split('}')[1]

                        if label == 'calculationArc':

                            temp_dict = {}

                            for key in children.keys():

                                if '}' in key:

                                    new_key = key.split('}')[1]
                                    temp_dict[new_key] = children.attrib[key]

                                else:

                                    temp_dict[key] = children.attrib[key]
                            
                            # Append to calculations
                            calculations.append(temp_dict)

            # If we are in _def.xml
            elif file.namespace_label == 'definition':
                
                # Iterate through definitionLink
                for element in elements:

                    # Iterate through each Link, grab only definitionArc
                    for children in element.iter():

                        label = children.tag.split('}')[1]

                        if label == 'definitionArc':

                            temp_dict = {}

                            for key in children.keys():

                                if '}' in key:

                                    new_key = key.split('}')[1]
                                    temp_dict[new_key] = children.attrib[key]

                                else:

                                    temp_dict[key] = children.attrib[key]
                            
                            # Append to definitions
                            definitions.append(temp_dict)
            
            # If we are in _lab.xml
            else:

                # Iterate through labelLink
                for element in elements:

                    # Iterate through each Link, grab label, THEN labelArc
                    for children in element.iter():

                        label = children.tag.split('}')[1]

                        if label == 'label':

                            temp_dict = {}

                            # Grab label text, if it is there
                            if children.text in ['', '\n', ' '] or isinstance(children.text,type(None)):
                                temp_dict['text'] = None
                            else:
                                temp_dict['text'] = children.text.strip()

                            # Grab label keys and attributes
                            for key in children.keys():

                                if '}' in key:

                                    new_key = key.split('}')[1]
                                    temp_dict[new_key] = children.attrib[key]

                                else:

                                    temp_dict[key] = children.attrib[key]
                            
                            # Append to labels
                            labels.append(temp_dict)


        return calculations, definitions, labels


    '''PARSE THE MAIN FILE (.HTM)'''

    def parseMain(self):
        
        # Define XBRL Instance Data Storage
        facts_nan = [] # Name, FactId, ContextRef, Value, Format
        facts_num = [] # Name, FactId, ContextRef, Value, Scale, Format, UnitRef
        grab = ['name', 'contextRef', 'unitRef','sign', 'scale', 'format']
        contexts = [] # ContextId, Dimensions...name1,value1,name2,value2... Instance, startDate, endDate
        units = [] # UnitId, Operator, Elements

        DimensionTuple = namedtuple("DimensionTuple", ["dimension", "value"])

        # if the first instance files is there parse it, else parse the main
        if self.instanceXML:
            tree = parse(self.instanceXML)

            # loop through all the elements

            for element in tree.iter():

                # we want to identify context, unit and ALL TAGS

                if 'context' in element.tag:

                    try:
                        context_temp_dict = {}
                        context_temp_dict['id'] = element.attrib['id']
                        context_temp_dict['dimensions'] = []

                        # Iterate through the context children

                        for children in element.iter():

                            # Get dimensions if available

                            if 'explicitMember' in children.tag:
                                
                                context_temp_dict['dimensions'].append(DimensionTuple(children.attrib['dimension'], children.text.strip()))

                            # Get instant date if available

                            elif 'instant' in children.tag:

                                context_temp_dict['instant'] = children.text.strip()
                                context_temp_dict['startDate'] = None
                                context_temp_dict['endDate'] = None

                            # Get period of dates if available

                            else:

                                context_temp_dict['instant'] = None

                                if 'startDate' in children.tag:

                                    context_temp_dict['startDate'] = children.text.strip()

                                if 'endDate' in children.tag:

                                    context_temp_dict['endDate'] = children.text.strip()

                        # Append to contexts
                        contexts.append(context_temp_dict)
                    except:
                        pass

                elif 'unit' in element.tag:

                    try:
                        unit_temp_dict = {}
                        unit_temp_dict['id'] = element.attrib['id']
                        unit_temp_dict['measures'] = []

                        for children in element.iter():
                            
                            if 'measure' in children.tag:

                                unit_temp_dict['measures'].append(children.text.strip())

                        # Append to units
                        units.append(unit_temp_dict)
                    except:
                        pass

                else:

                    try:
                        if "decimals" in element.attrib.keys() or "unitRef" in element.attrib.keys():
                            
                            numfact_temp_dict = {}
                            if 'us-gaap' in element.tag:
                                numfact_temp_dict['name'] = 'us-gaap:' + element.tag[element.tag.rfind('}')+1:]
                            elif 'dei' in element.tag:
                                numfact_temp_dict['name'] = 'dei:' + element.tag[element.tag.rfind('}')+1:]
                            elif 'srt' in element.tag:
                                numfact_temp_dict['name'] = 'srt:' + element.tag[element.tag.rfind('}')+1:]
                            else:
                                taxonomy = element.tag[element.tag.rfind('.org/')+5:element.tag.rfind('/')]
                                numfact_temp_dict['name'] = taxonomy + ':' + element.tag[element.tag.rfind('}')+1:]

                            for key in element.keys():

                                if key in grab:
                                    numfact_temp_dict[key] = element.attrib[key]
                                    numfact_temp_dict['value'] = element.text.strip()
                                else:
                                    pass
                            
                            if numfact_temp_dict == {} or numfact_temp_dict['value'] == '\n':
                                pass
                            else:
                                # Append to facts
                                facts_num.append(numfact_temp_dict)
                        
                        else:
                            
                            nanfact_temp_dict = {}

                            if 'us-gaap' in element.tag:
                                nanfact_temp_dict['name'] = 'us-gaap:' + element.tag[element.tag.rfind('}')+1:]
                            elif 'dei' in element.tag:
                                nanfact_temp_dict['name'] = 'dei:' + element.tag[element.tag.rfind('}')+1:]
                            elif 'srt' in element.tag:
                                nanfact_temp_dict['name'] = 'srt:' + element.tag[element.tag.rfind('}')+1:]
                            else:
                                taxonomy = element.tag[element.tag.rfind('.org/')+5:element.tag.rfind('/')]
                                nanfact_temp_dict['name'] = taxonomy + ':' + element.tag[element.tag.rfind('}')+1:]

                            for key in element.keys():

                                if key in grab:
                                    nanfact_temp_dict[key] = element.attrib[key]
                                    nanfact_temp_dict['value'] = element.text.strip()
                                else:
                                    pass
                            
                            if nanfact_temp_dict == {} or nanfact_temp_dict['value'] == '\n':
                                pass
                            else:
                                # Append to facts
                                facts_nan.append(nanfact_temp_dict)
                    
                    except:
                        pass
        
        
        
       # IF  the instance file is not able to parse due to due no file, then parse the main 
        else:

            # load the XML file
            tree = parse(self.file_htm)

            # loop through all the elements
            for element in tree.iter():

                # we want to find context, unit, nonNumeric, nonFraction

                if 'context' in element.tag:

                    try:

                        context_temp_dict = {}
                        context_temp_dict['id'] = element.attrib['id']
                        context_temp_dict['dimensions'] = []

                        # Iterate through the context children

                        for children in element.iter():

                            # Get dimensions if available

                            if 'explicitMember' in children.tag:
                                
                                context_temp_dict['dimensions'].append(DimensionTuple(children.attrib['dimension'], children.text.strip()))

                            # Get instant date if available

                            elif 'instant' in children.tag:

                                context_temp_dict['instant'] = children.text.strip()
                                context_temp_dict['startDate'] = None
                                context_temp_dict['endDate'] = None

                            # Get period of dates if available

                            else:

                                context_temp_dict['instant'] = None

                                if 'startDate' in children.tag:

                                    context_temp_dict['startDate'] = children.text.strip()

                                if 'endDate' in children.tag:

                                    context_temp_dict['endDate'] = children.text.strip()

                        # Append to contexts
                        contexts.append(context_temp_dict)

                    except:

                        pass

                if 'unit' in element.tag:

                    try:

                        unit_temp_dict = {}
                        unit_temp_dict['id'] = element.attrib['id']
                        unit_temp_dict['measures'] = []

                        for children in element.iter():
                            
                            if 'measure' in children.tag:

                                unit_temp_dict['measures'].append(children.text.strip())

                        # Append to units
                        units.append(unit_temp_dict)

                    except:

                        pass

                if 'nonNumeric' in element.tag:

                    try:

                        nanfact_temp_dict = {}

                        for key in element.keys():

                            if key in grab:

                                nanfact_temp_dict[key] = element.attrib[key]
                                nanfact_temp_dict['value'] = element.text.strip()

                            else:
                                
                                pass
                        
                        if nanfact_temp_dict == {} or nanfact_temp_dict['value'] == '\n':

                            pass

                        else:

                            # Append to facts
                            facts_nan.append(nanfact_temp_dict)

                    except:

                        pass

                if 'nonFraction' in element.tag:

                    try:

                        numfact_temp_dict = {}

                        for key in element.keys():

                            if key in grab:

                                numfact_temp_dict[key] = element.attrib[key]
                                numfact_temp_dict['value'] = element.text.strip()

                            else:
                                
                                pass
                        
                        if numfact_temp_dict == {} or numfact_temp_dict['value'] == '\n':

                            pass

                        else:

                            # Append to facts
                            facts_num.append(numfact_temp_dict)

                    except:

                        pass


        return facts_nan, facts_num, contexts, units


    '''PLACE EVERYTHING INTO A PANDAS DATAFRAME'''

    def createDataFrames(self, calculations:list, definitions:list, labels:list, factsNan:list, factsNum:list, contexts:list, units:list):

        calculationsDF = pd.DataFrame(calculations)
        definitionsDF = pd.DataFrame(definitions)
        labelsDF = pd.DataFrame(labels)
        factsNan_DF = pd.DataFrame(factsNan)
        factsNum_DF = pd.DataFrame(factsNum)
        contextsDF = pd.DataFrame(contexts)
        unitsDF = pd.DataFrame(units)
        
        
        return calculationsDF, definitionsDF, labelsDF, factsNan_DF, factsNum_DF, contextsDF, unitsDF