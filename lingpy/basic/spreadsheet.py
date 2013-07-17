"""
This module provides a basic class for reading in a simple spreadsheet (delimited text file) for concepts and words in a set of languages.
"""

__author__="Steven Moran"
__date__="2013-04"

# external imports
import regex as re
import sys 
import codecs
import unicodedata
from time import gmtime, strftime

# internal imports
from ..settings import rcParams
from ..sequence.ngram import *
from ..read.csv import *
from ..convert.csv import wl2csv

class Spreadsheet:
    """
    Basic class for reading spreadsheet data.
    """
    def __init__(self, 
                 filename,
                 fileformat = None, # ? what do you need this for? req'd in read.csv
                 dtype = None, # flag for different datatypes; required in read.csv 
                 comment = '#',
                 sep = '\t', # column separator
                 language_id = "NAME", # think about this variable name
                 meanings = "CONCEPT", # explicit name of column containing concepts
                 blacklist = "", # filename path to blacklist file
                 conf = "", # spreadsheet .rc file
                 cellsep = ';', # cell separator, separates forms in the same cell
                 verbose = False,
                 **keywords
                 ):

        self.filename = filename
        self.fileformat = fileformat
        self.dtype = dtype
        self.comment = comment
        self.sep = sep
        self.language_id = language_id
        self.meanings = meanings
        self.blacklist = blacklist
        self.conf = conf
        self.cellsep = cellsep
        self.verbose = verbose

        # set up matrix
        self.matrix = []
        self._init_matrix()
        self._normalize()
        self._blacklist()
        self._prepare()

    def _blacklist(self):
        """
        Remove anything in the spreadsheet that's specified in the blacklist file.
        """
        if not os.path.isfile(self.blacklist):
            if self.verbose:
                print("[i] There is no blacklist specified at the follow file path location. Proceeding without blacklist.")
            return

        blacklist_file = codecs.open(self.blacklist, "r")
        # loop through the blacklist file and compile the regexes
        rules = []
        replacements = []
        for line in blacklist_file:
            line = line.strip()
            # skip any comments
            if line.startswith("#") or line == "":
                continue
            line = unicodedata.normalize("NFD", line)
            rule, replacement = line.split(",") # black list regexes must be comma delimited
            rule = rule.strip() # just in case there's trailing whitespace
            replacement = replacement.strip() # because there's probably trailing whitespace!
            rules.append(re.compile(rule))
            replacements.append(replacement)
        blacklist_file.close()

        # blacklist the spreadsheet data - skip the header row
        for i in range(1, len(self.matrix)):
            for j in range(0, len(self.matrix[i])):
                for k in range(0, len(rules)):
                    match = rules[k].search(self.matrix[i][j])
                    if not match == None:
                        match = re.sub(rules[k], replacements[k], self.matrix[i][j])                
                        if self.verbose:
                            print("[i] Replacing <"+self.matrix[i][j]+"> ["+str(i)+","+str(j)+"] with <"+match+">.")
                        self.matrix[i][j] = match.strip()

    def _init_matrix(self):
        """
        Create a 2D array from the CSV input and Unicode normalize its contents
        """
        # TODO: check if spreadsheet is empty and throw error
        spreadsheet = csv2list(
            self.filename, 
            self.fileformat, 
            self.dtype, 
            self.comment, 
            self.sep
            # strip_lines = False
            )

        # columns that have language data
        language_indices = []

        # first row must be the header in the input; TODO: add more functionality
        header = spreadsheet[0] 

        if self.verbose: print(header[0:10])
        
        for i,cell in enumerate(header):
            head = cell.strip()
            if self.verbose: print(head)
            if head == self.meanings:
                self.concepts = i
            if self.language_id in head:
                language_indices.append(i)

        matrix_header = []
        matrix_header.append(header[self.concepts])        
        for i in language_indices:
            matrix_header.append(header[i].replace("name", "").strip())
        self.matrix.append(matrix_header)

        # append the concepts and words in languages and append the rows
        for i in range(1, len(spreadsheet)): # skip the header row
            matrix_row = [] # collect concepts and languages to add to matrix
            temp = []
            for j in range(0, len(spreadsheet[i])):
                if j == self.concepts:
                    matrix_row.append(spreadsheet[i][j])
                if j in language_indices:
                    temp.append(spreadsheet[i][j])
            for item in temp:
                matrix_row.append(item)
            self.matrix.append(matrix_row)

    def _normalize(self):
        """ 
        Function to Unicode normalize (NFD) cells in the matrix.
        """
        for i in range(0, len(self.matrix)):
            for j in range(0, len(self.matrix[i])):
                normalized_cell = unicodedata.normalize("NFD", self.matrix[i][j])
                if not normalized_cell == self.matrix[i][j]:
                    if self.verbose:
                        print("[i] Cell at <"+self.matrix[i][j]+"> ["+str(i)+","+str(j)+"] not in Unicode NFD. Normalizing.")
                    self.matrix[i][j] = normalized_cell
    
    def _prepare(self,full_rows = False):
        """
        Prepare the spreadsheet for automatic pass-on to Wordlist.
        """
        # XXX we now assume that the matrix is 'normalized',i.e. that it only
        # contains concepts and counterparts, in later versions, we should make
        # this more flexible by adding, for example, also proto-forms, or
        # cognate ids

        # define a temporary matrix with full rows
        if not full_rows:
            matrix = self.matrix
        else:
            matrix = self.get_full_rows()

        # create the dictionary that stores all the data
        d = {}

        # iterate over the matrix
        idx = 1
        for i,line in enumerate(matrix[1:]):
            # only append lines that really work!
            if line:
                # get the concept
                concept = line[0].strip()

                if concept:

                    # get the rest
                    for j,cell in enumerate(line[1:]):

                        # get the language
                        language = matrix[0][j+1].replace(self.language_id,'').strip()

                        # get the counterparts
                        counterparts = [x.strip() for x in cell.split(self.cellsep)]

                        # append stuff to dictionary
                        for counterpart in counterparts:
                            if counterpart:
                                d[idx] = [concept,language,counterpart]
                                idx += 1

        # add the header to the dictionary
        d[0] = ["concept","doculect","counterpart"]

        # make the dictionary an attribute of spreadsheet
        self._data = dict([(k,v) for k,v in d.items() if k > 0])

        # make empty meta-attribute
        self._meta = dict(
                filename = self.filename
                )

        # make a simple header for wordlist import
        self.header = dict([(a,b) for a,b in zip(d[0],range(len(d[0])))])

    def get_full_rows(self):
        """
        Create a 2D matrix from only the full rows in the spreadsheet.
        """
        full_row_matrix = []

        for row in self.matrix:
            is_full = 1

            for token in row:
                if token == "":
                    is_full = 0

            if is_full:
                full_row_matrix.append(row)

        return(full_row_matrix)

    def print_doculect_character_counts(self, doculects=1):
        for i in range(0, len(self.matrix)):
            print(self.matrix[i])
            for j in range(doculects, len(self.matrix[i])):
                if not self.matrix[i][j] == "":
                    print(self.matrix[i][j])
                    
    def stats(self):
        """
        Convenience function to get some stats data about the spreadsheet
        """
        total_entries = 0
        entries = []
        header = self.matrix[0]
        total_cells = len(self.matrix)*len(header)

        for item in header:
            entries.append(0)

        for row in self.matrix:
            for i in range(0, len(row)):
                if not row[i] == "":
                    total_entries += 1
                    entries[i] = entries[i] + 1
        print()
        print("Simple matrix stats...")
        print()
        print("total rows in matrix:", len(self.matrix))
        print("total cols in matrix:", len(header))
        print("total possible cells:", total_cells)
        print("total filled cells  :", str(total_entries), "("+str((total_entries*1.0)/total_cells*100)[:4]+"%)")
        print()
        print("total cells per column:")
        for i in range(0, len(header)):
            print(header[i]+"\t"+str(entries[i]-1)) # do not include the header in count
        print()
    
    def pprint(self, delim="\t"):
        """
        Pretty print the matrix
        """
        for i in range(0, len(self.matrix)):
            row = ""
            for j in range(0, len(self.matrix[i])):
                row += self.matrix[i][j]+delim
            row = row.rstrip(delim)
            print(row)

    def print_qlc_format(self):
        """
        Print "simple" QLC format.
        """
        print("@input file: "+self.filename)
        print("@date: "+strftime("%Y-%m-%d %H:%M:%S", gmtime()))
        print("#")
        print("LANGUAGE"+"\t"+"CONCEPT"+"\t"+"COUNTERPART")

        id = 0
        for i in range(1, len(self.matrix)):
            for j in range(1, len(self.matrix[i])):
                id += 1
                if self.matrix[i][j] == "":
                    row = str(id)+"\t"+self.header[j]+"\t"+self.matrix[i][0]+"\t"+"NaN"
                else:
                    row = str(id)+"\t"+self.header[j]+"\t"+self.matrix[i][0]+"\t"+self.matrix[i][j]
                print(row)        

    def _output(self, fileformat, **keywords):
        """
        Output the matrix into Harry Potter format.
        """

        defaults = dict(
                filename = "lingpy-{0}".format(_timestamp()),
                meta = self._meta
                )
        for k in defaults:
            if k not in keywords:
                keywords[k] = defaults[k]
        
        # use wl2csv to convert if fileformat is 'qlc'
        if fileformat in ['qlc','csv']:
            if fileformat == 'csv':
                print(rcParams['deprecation_warning'].format('csv','qlc'))
            wl2csv(
                    self.header,
                    self._data,
                    **keywords
                    )

    def output(
            self,
            fileformat,
            **keywords
            ):
        """
        Write Spreadsheet to different formats.
        """

        return self._output(fileformat,**keywords)


