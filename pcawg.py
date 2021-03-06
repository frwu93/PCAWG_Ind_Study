import pandas as pd
import os
from BitVector import BitVector
import sys
import time 
import csv
import vcf
import gzip
import shutil
import winsound



def essentialElementReadIn(file_path):
    """Reads in essential element coordinates from TSV file and returns a map containing the information. Maps chromosome number
    to a list of that chromosome's essential element coordinates.

    Args:
        file_path (str): file path of desired file

    Returns:
        dict: Dictionary mapping each chromosome to its essential element coordinates. Key: (str) chromosome number. 
        Value: (list) list of essential element coordinates in format of [start1, end1, start2, end2, ... , start[n], end[n]]
    """
    df = pd.read_csv(file_path, sep = "\t", names = ['Chr_Num', 'Start', 'End'])

    #cleaning data
    df.Chr_Num = df.Chr_Num.str[3:] #getting rid of Chr tag
    df[['Start', 'End']] = df[["Start", 'End']].apply(pd.to_numeric) #changing start and end coords to ints

    #creating map
    chromosome_coord_map = {}

    for index, row in df.iterrows():
        chrom_num = row['Chr_Num']
    
        if chrom_num not in chromosome_coord_map.keys():
            chromosome_coord_map[chrom_num] = []
        chromosome_coord_map[chrom_num].extend([row['Start'], row['End']])

    return chromosome_coord_map

def chromosomeLengthReadIn(file_path):
    """Reads in chromosome lengths from CSV file and returns a map containing the information. Maps chromosome number to 
    its corresponding length.

    Args:
        file_path (str): file path of desired file

    Returns:
        dict: Dictionary mapping each chromosome to its corresponding length. Key: (str) chromosome number. Value: (int) length of chromosome in bp
    """
    df = pd.read_csv(file_path, names = ['Chr_Num', 'Length'])
    df['Length'] = pd.to_numeric(df['Length']) 

    chromosome_length_map = {}

    for index, row in df.iterrows():
        chrom_num = row['Chr_Num']
        chromosome_length_map[chrom_num] = row['Length']

    return chromosome_length_map


def constructBitVector(chromosome_coord_map, chromosome_length_map, chr_num):
    """Constructs a bit vector for an individual chromosome.

    Args:
        chromosome_coord_map (dict): map of chromosomes and desired coordinates. Key: (str) chromosome number. Value: (list) Desired coordinates 
        chromosome_length_map (dict): map of chromosomes to their lengths. Key: (str) chromosome number. Value: (int) Length of chromosome. 
        chr_num (str): chromosome number 

    Returns:
        BitVector: a bit vector representing regions in chromosome that exhibited unusual growth activity.
        0 for coordinates not associated with cell growth, 1 for coordinates associated with cell growth
    """  

    #visual indicator for running purposes
    print("CHR NUM = " + str(chr_num))
    print("CHR Length = " + str(chromosome_length_map[chr_num]))


    currIndex = 0

    bv  = BitVector(size = chromosome_length_map[chr_num]) # initializes a bit vector of 0's of size of chromosome + 1

    coord_lst = chromosome_coord_map[chr_num]

    for i in range(0, len(coord_lst)-1, 2): #going through coordinate list
        start = coord_lst[i]  #start coordinate
        print(start)
        stop = coord_lst[i+1] #stop coordinate
        for i in range(start, stop + 1):
            bv[i] = 1

    return bv


def constructBitVectorMap(chromosome_coord_map, chromosome_length_map):
    """Constructs and returns a map of chromosomes and their corresponding bit vectors. Each bit vector represents a chromosome's
    essential element coordinates. Key: (str) chromosome number. Value: (BitVector) bit vector representation of coordinates for that chromosome

    Args:
       chromosome_coord_map (dict): map of chromosomes and desired coordinates. Key: (str) chromosome number. Value: (list) Desired coordinates 
       chromosome_length_map (dict): map of chromosomes to their lengths. Key: (str) chromosome number. Value: (int) Length of chromosome. 

    Returns:
        dict: map of chromosomes to their corresponding bit vector
    """

    bitVectorMap = {}

    for chr_num in chromosome_coord_map.keys():
        bv = constructBitVector(chromosome_coord_map, chromosome_length_map, chr_num)
        bitVectorMap[chr_num] = bv
   
    return bitVectorMap

def constructCoordinateList(bv):
    """[NOT IN USE] Constructs a list of [start,end] coordinates from a BitVector

    Args:
        bv (BitVector): The bit vector to be read

    Returns:
        list: list of start and end coordinates represented in the BitVector
    """
    bit_runs = bv.runs()
    coord_lst = []
    currentIndex = 0
    for i in range(len(bit_runs)):
        if "1" in bit_runs[i]:
            coord_lst.append(currentIndex)
            coord_lst.append(currentIndex + len(bit_runs[i]) - 1)
        currentIndex+= len(bit_runs[i]) 
    
    return coord_lst

def constructCoordinateMap(bitVectorMap):
    """[NOT IN USE] Constructs a coordinate map based off of a bit vector map. Used to turn a set of BitVector chromosomes into lists of coordinates
       one list per chromosome.

    Args:
        bitVectorMap (dict): a dict mapping the chromosome number (str) to the BitVector that represents it

    Returns:
        dict: a dict mapping the chromosome number (str) to a list of start,end coordinates
    """
    coord_map = {}
    for chr in bitVectorMap.keys():
        coord_lst = constructCoordinateList(bitVectorMap[chr])
        coord_map[chr] = coord_lst

    return coord_map

def writeCoordinates(coord_map, filename):
    """[NOT IN USE] Writes the coordinates from the coordinate map into an output file

    Args:
        coord_map (dict): a dict mapping the chromosome number (str) to a list of start,end coordinates
        filename (str): name of the output file
    """
    for chr in coord_map:
        pairs = []
        lst = coord_map[chr]
        for i in range(0, len(lst)-1, 2):
            temp = ["chr" + chr, lst[i], lst[i+1]]
            pairs.append(temp)
        print(pairs)
        pairs = pd.DataFrame(pairs)
        pairs.to_csv(filename, index=False, sep = "\t", header = False, mode = 'a')

def decompressGZFiles(folder, directory):
    """Decompresses all .vcf.gz files to a .vcf file, stored in the given directory

    Args:
        folder (str): location of the folder containing the .vcf.gz files
        directory (str): location of the folder to store the decompressed .vcf files
    """
    print("wtf", folder)
    count = 0
    for entry in os.scandir(folder):
        if(entry.path.endswith('.vcf.gz')):
            count+=1
            print(entry)
            decompressedFileName = directory + os.path.basename(entry)[:len(os.path.basename(entry))-3]
            with gzip.open(entry, 'rb') as f_in:
                with open(decompressedFileName, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        if(count == 50):
            sys.exit(1)
    
def compareVCFtoBitVectorMap(entry, bitVectorMap):
    """Runs comparison of a single VCF to the essential elements, which is stored as a map of BitVectors.

    Args:
        entry (str): name of VCF file
        bitVectorMap (dict): a dict mapping the chromosome number (str) to the BitVector that represents it

    Returns:
        list: A list of entries in the VCF that coincide with the BitVector map
    """
    hits = []
    vcf_reader = vcf.Reader(open(entry, 'r'))
    for record in vcf_reader:
        try:
            if record.CHROM == 'Y' or record.CHROM not in bitVectorMap:
                continue
            #navigate to chromosome
            bv = bitVectorMap[record.CHROM]
            if (bv[record.POS] == 1):
                hits.append([str(record), record.INFO])
        except Exception as e:
            winsound.Beep(440, 500)
            print(entry, record.CHROM, record.POS)
            raise e
    print(len(hits))
    return hits
    

def compare(directory, bitVectorDict):
    results = {}
    for entry in os.scandir(directory):
        for bvMap in bitVectorDict:
            hits = compareVCFtoBitVectorMap(entry, bitVectorDict[bvMap])
            if (len(hits)>0):
                if bvMap not in results:
                    results[bvMap] = {}
                results[bvMap][entry] = hits

    return results
            


