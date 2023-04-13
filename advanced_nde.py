# -*- coding: utf-8 -*-
"""
Created on Tue Nov  1 15:58:59 2022

@author: ajveh
"""


import h5py
import json
import sys
import posixpath
import numpy as np
import collections
import pdb
dimensions_with_arrays_workaround = False # Set to false once source build fixed
andefile_loader_registry = {} # dictionary indexed by ande class name of (inheritance_depth,readerclass)

class andefile_readrecording_base(object):  
    ande_classes = None #set of ande class strings
    ande_class_tags = None #ANDE class tags a set of strings
    fh = None #HDF5 file handle
    recpath = None # Conceptual recording path
    ande_recording_version = None # version string
    ande_recording_label = None # name of this recording within its parent
    metadata = None # Dictionary of metadata
    hdf_fh = None
    filemap = None
    classmap = None # Dictionary by ande classname of the python class to instantiate
    paramblock = None # User parameters to be passed around
    def __init__(self,ande_classes,recpath,hdf_fh,filemap,classmap,paramblock):
        self.metadata = {}
        self.ande_classes = ande_classes
        self.recpath = recpath
        self.hdf_fh = hdf_fh
        self.filemap = filemap
        self.classmap = classmap
        self.paramblock = paramblock
        
        # confirm required ande_classes
        if "ande_recording" not in ande_classes:
            raise ValueError("andefile_readrecording_base: recording %s is not an ande_recording" %recpath)
        if not "ande_recording-version" in hdf_fh.attrs.keys():
            raise ValueError("andefile_readrecording_base: recording %s does not specify an ande_recording-version" %recpath)
        self.ande_recording_version = hdf_fh.attrs["ande_recording-version"]
        self.ande_recording_label = hdf_fh.attrs["ande_recording-label"]
        (grouppath,entryname) = posixpath.split(recpath)
        if entryname != self.ande_recording_label:
            if self.ande_recording_label == "dgs_root":
                self.ande_recording_label = ""
                pass
            else:
                raise ValueError("andefile_readrecording_base: recording %s label %s does not match group entry %s" %(recpath,self.ande_recording_label,entryname))
            pass
        self.ande_class_tags = hdf_fh.attrs["ande_class-tags"]
        if "ande_recording-metadata" in hdf_fh[recpath].keys():
            self.metadata = hdf_fh[recpath]["ande_recording-metadata"].attrs
            pass
        pass
        
    def define_rec(self):
        pass
    def read(self,rec):
        pass
        #__del__(self):
        #   custom deconstructor
        
    def __repr__(self) -> str:
        return "<ANDE loader class for channel '"+posixpath.join("/",posixpath.split(self.recpath)[1])+"'>"
    pass
    
    
# Define our subclasses here
class andefile_readarray(andefile_readrecording_base):
    hidden = None # boolean
    numarrays = None # integer
    array_version = None # version string
    def __init__(self,ande_classes,recpath,hdf_fh,filemap,classmap,paramblock):
        super().__init__(ande_classes,recpath,hdf_fh,filemap,classmap,paramblock)
        self.hidden = False
        if not "ande_array" in ande_classes:
            raise ValueError("andefile_readarray: recording %s is not an ande_array" %recpath)
        if not "ande_array-version" in hdf_fh[self.recpath].attrs.keys():
            raise ValueError("andefile_readarray: recording %s does not specify an ande_array-version" %recpath)
        self.numarrays = hdf_fh[self.recpath].attrs["ande_array-numarrays"]
        pass
    
    def define_rec(self):
        array_dimlen = []
        array_ordering = []
        array_names = []
        for arraynum in range(self.numarrays):
            arrayname_attr = "ande_array-name-%d"%arraynum
            dimlenC_attr = "ande_array-dimlenC-%d"%arraynum
            dimlenF_attr = "ande_array-dimlenF-%d"%arraynum 
            array_names.append(self.hdf_fh[self.recpath].attrs[arrayname_attr])
            if dimlenC_attr in self.hdf_fh[self.recpath].keys():
                array_dimlen.append(self.hdf_fh[self.recpath][dimlenC_attr][()])
                array_ordering.append("C")
                pass
            elif dimlenF_attr in self.hdf_fh[self.recpath].keys():
                array_dimlen.append(self.hdf_fh[self.recpath][dimlenF_attr][()])
                array_ordering.append("F")
                pass
            else:
                raise ValueError("Array dimensions (%s or %s) not found for recording %s"%(dimlenC_attr,dimlenF_attr,self.recpath))
        return self.classmap["ande_array"](ande_class_tags = self.ande_class_tags,
                                   ande_metadata = self.metadata,
                                   ande_recording_version = self.ande_recording_version,
                                   ande_recording_label = self.ande_recording_label,
                                   ande_array_version = self.array_version,
                                   ande_paramblock = self.paramblock,
                                   ande_array_names = array_names,
                                   ande_array_dimlen = array_dimlen,
                                   ande_array_ordering = array_ordering,
                                   ande_arrays = [])
    def read(self,rec):
        #our_loadedobj = self.filemap[self.recpath][1]
        for arraynum in range(self.numarrays):
            array_attr = "ande_array-array-%d"%arraynum
            h5obj = self.hdf_fh[self.recpath][array_attr]
            array_ordering = rec.ande_array_ordering[arraynum]
            nativetype = h5obj.dtype
            dimlen = rec.ande_array_dimlen[arraynum]
            rec.ande_arrays.append(h5obj[()].reshape(dimlen,order = array_ordering))
            pass
        pass
    pass
   
andefile_loader_registry["ande_array"] = (1,andefile_readarray) # Add readarray class into the loader registry
    
        
class andefile_readgroup(andefile_readrecording_base):
    group_version = None # version string
    group_subloaders = None # dictionary of loader objects indexed by recording name
    def __init__(self,ande_classes,recpath,hdf_fh,filemap,classmap,paramblock):
        super().__init__(ande_classes,recpath,hdf_fh,filemap,classmap,paramblock)
        # COnfirm the required ande classes
        if not "ande_group" in ande_classes:
            raise ValueError("andefile_readgroup: recording %s is not an ande_group" %recpath)
        if not "ande_group-version" in hdf_fh.attrs.keys():
            raise ValueError("andefile_readgroup: recording %s does not specify an ande_group-version" %recpath)
        self.group_version = hdf_fh.attrs.__getitem__("ande_group-version")
        self.group_subloaders = {}
        for subgroup_name in hdf_fh["ande_group-subgroups"]:
            subgroup_recpath = posixpath.join(recpath,"ande_group-subgroups",subgroup_name)
            #sys.stderr.write("Loading subgroups, classmap value = %s \n"%(classmap))
            #subgroup_loader = andefile_loadrecording(hdf_fh["ande_group-subgroups"][subgroup_name],subgroup_recpath,hdf_fh,filemap,classmap,paramblock)
            subgroup_loader = andefile_loadrecording(subgroup_recpath,hdf_fh,filemap,classmap,paramblock)
            self.filemap[posixpath.join("/",posixpath.split(subgroup_recpath)[1])] = [subgroup_loader,None] # filemap contains [loaderobj, loadedobj], but loadedobj not yet available.
            self.group_subloaders[subgroup_name] = subgroup_loader
            pass
        pass
    def define_rec(self):
        #sys.stderr.write("Readgroup Called classmap before %s \n"%(classmap))
        return self.classmap["ande_group"](ande_class_tags = self.ande_class_tags,
                                   ande_metadata = self.metadata,
                                   ande_recording_version = self.ande_recording_version,
                                   ande_recording_label = self.ande_recording_label,
                                    ande_group_version = self.group_version,
                                   ande_paramblock = self.paramblock,
                                   ande_group_entries = collections.OrderedDict())
        
    def read(self,rec):
        #our_loadedobj = self.filemap[self.recpath]
        for subgroup_name in self.hdf_fh["ande_group-subgroups"]:
            subgroup_recpath = posixpath.join(self.recpath,"ande_group-subgroups",subgroup_name)
            rec.ande_group_entries[subgroup_name] = self.filemap[posixpath.join("/",posixpath.split(subgroup_recpath)[1])][1] # extract loadedobj from filemap
            pass
            
        pass
    pass
   
andefile_loader_registry["ande_group"] = (1,andefile_readgroup) # Add readgroup class into the loader registry     

# overridable classes (see classmap) for instantiating the loaded data structures

class ande_recording(object):
    ande_metadata = None
    ande_recording_version = None
    ande_recording_label = None
    ande_classes = None
    ande_class_tags = None
    ande_paramblock = None
    def __init__(self,**kwargs):
        for argname in kwargs:
            if hasattr(self,argname):
                setattr(self,argname,kwargs[argname])
                pass
            else:
                raise ValueError("unknown attribute %s"%(argname))
            pass
        pass
    pass

class ande_array(ande_recording):
    ande_arrays = None # List of numpy arrays
    ande_array_dimlen = None
    ande_array_ordering = None
    ande_array_version = None
    ande_array_names = None
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        #pdb.set_trace()
        # add in axis attributes for all defined axes for array number 0
        if len(self.ande_array_dimlen) == 0:
            return # nothing to do if there aren't any arrays
        for axis in range(len(self.ande_array_dimlen[0])): # go through each axis of the index 0 array
            inival = 0
            if ("ande_array-axis%d_offset"%axis) in self.ande_metadata:
                inival = float(self.ande_metadata["ande_array-axis%d_offset"%axis])
                pass
            step = 1
            if ("ande_array-axis%d_scale"%axis) in self.ande_metadata:
                step = float(self.ande_metadata["ande_array-axis%d_scale"%axis])
                pass
            #import pdb
            if axis < 3:
                coord = chr(ord("x")+axis)+" position" # x,y, or z
                pass
            elif axis == 3:
                coord = "w position"
                pass
            elif axis < 26:
                coord = chr(ord("a")+axis-4)+" position" # a-v
                pass
            else:
                raise ValueError("Too many axes")
            if ("ande_array-axis%d_coord"%axis) in self.ande_metadata:
                coord = self.ande_metadata["ande_array-axis%d_coord"%axis]
                pass
            units = "meters"
            if ("ande_array-axis%d_offset-units"%axis) in self.ande_metadata:
                units = self.ande_metadata["ande_array-axis%d_offset-units"%axis]
                pass
            setattr(self,"axis%d"%axis,inival+step*np.arange(self.ande_array_dimlen[0][axis]))
            setattr(self,"extent%d"%axis,(inival-step/2,inival+self.ande_array_dimlen[0][axis]*step-step/2))
            setattr(self,"coord%d"%axis,coord)
            setattr(self,"units%d"%axis,units)
            pass
        self.ampl_coord = "Value"
        if "ande_array-ampl_coord" in self.ande_metadata:
            self.ampl_coord = self.ande_metadata["ande_array-ampl_coord"]
            pass
        self.ampl_units = "Unitless"
        if "ande_array-ampl_units" in self.ande_metadata:
            self.ampl_units = self.ande_metadata["ande_array-ampl_units"]
            pass
        pass
    
    def __str__(self):
        if self.ande_arrays is None:
            return "Incomplete ande_array object"
        assert(len(self.ande_arrays) == len(self.ande_array_names))
        array_descrs = ["          %7d:     %10s  %s"%(index,self.ande_array_names[index],str(self.ande_arrays[index].shape)) for index in range(len(self.ande_array_names))]
        return "ande_array array_index  array_name  dimensions \n          ------------------------------------- \n%s\n"%("\n".join(array_descrs))
        
    def __repr__(self):
        return str(self)
    pass

class ande_group(ande_recording):
    #ande_subgroups = None
    ande_group_version = None
    ande_group_entries = None
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        pass
    pass
        
            
def andefile_loadrecording(recording_path,hdf_fh,filemap,classmap,paramblock=None):
    #sys.stderr.write("Classmap at start of load recording %s \n"%(classmap))
    deepest_depth = 0
    deepest_class = None
    deepest_loaderfunc = None
    ande_classes = hdf_fh[recording_path].attrs.__getitem__("ande-classes")
    for classname in ande_classes:
        if classname in andefile_loader_registry:
            (depth, loaderfunc) = andefile_loader_registry[classname]
            if depth > deepest_depth:
                deepest_loaderfunc = loaderfunc
                deepest_depth = depth
                deepest_class = classname
                pass
            elif depth == deepest_depth:
                raise ValueError("andefile_loadrecording: Error loading recording %s: Recording has two classes %s and %s which are at the same depth (%u) in the hierarchy, which is not allowed." %(recording_path, deepest_class, classname,depth))
            pass
        elif classname == "ande_recording":
            pass            
        else:
            sys.stderr.write("andefile_loadrecording: Warning: Unrecognised class %s; using superclass instead \n" %(classname))
            pass
        pass
    if deepest_loaderfunc is None:
        raise ValueError("andefile_loadrecording: Recording %s does not specify any known classes" %recording_path)
    
    #sys.stderr.write("Pre-readerobj classmap check %s \n"%(classmap))
    #recording_path = posixpath.join(recording_path,deepest_class)
    readerobj = deepest_loaderfunc(ande_classes,recording_path,hdf_fh,filemap,classmap,paramblock)
    #sys.stderr.write("Loader function: %s \n"%(readerobj))
    #sys.stderr.write("Associated Classmap %s \n"%(classmap))
    
    return readerobj


def andefile_loadfile(filename,classmap={"ande_group" : ande_group, "ande_array" : ande_array},paramblock = None):
    hdf_fh = h5py.File(filename,'r')
    filemap = {} # indexed by recording path, contains list{loaderobj,loadedobj}
    # the jsons will be unecessary for the old format.
    #ande_json_string = hdf_fh["ande_json"][()]
    #ande_json = json.loads(ande_json_string)
    #sys.stderr.write("Classmap Passed in loaderfunc %s \n"%(classmap))
    readerobj = andefile_loadrecording("/",hdf_fh,filemap,classmap,paramblock)
    filemap["/"] = [readerobj,None]
    for path in filemap:
        filemap_entry = readerobj.filemap[path] 
        loaderobj = filemap_entry[0]
        filemap_entry[1] = loaderobj.define_rec()
        #sys.stderr.write("Classmap after define rec %s \n"%(classmap))
        #filemap_entry[1] = loaderobj.define_rec(classmap,paramblock)
        
        pass
    for path in filemap:
        filemap_entry = filemap[path] 
        (loaderobj,loadedobj) = filemap_entry
        #if loaderobj is None:
        #    continue
        loaderobj.read(loadedobj)
        pass
    # return a dictionary with just the loaded objects
    loaded = {}
    for objname in filemap.keys():
        loaded[objname] = filemap[objname][1]
    hdf_fh.close()
    return loaded

if __name__ == "__main__":
    from matplotlib import pyplot as plt
    if len(sys.argv) < 2:
        print("usage: %s <filename.ande>"%sys.argv[0])
        sys.exit(0)
        pass
    # Simple example of a generic viewer
    filename = sys.argv[1]
    loaded = andefile_loadfile(filename)
    for recpath in loaded:
        rec = loaded[recpath]
        if isinstance(rec,ande_array):
            if len(rec.ande_arrays) == 1:
                if len(rec.ande_array_dimlen[0]) == 1:
                    # 1-D waveform
                    plt.figure()
                    plt.plot(rec.axis0,rec.ande_arrays[0],"-")
                    plt.xlabel("%s (%s)"%(rec.coord0,rec.units0))
                    plt.ylabel("%s (%s)"%(rec.ampl_coord,rec.ampl_units))
                    plt.title(recpath)
                    pass
                if len(rec.ande_array_dimlen[0]) >= 2:
                    # Image or stack of images
                    num_images = np.prod(rec.ande_array_dimlen[0][2:])
                    (nx,ny) = rec.ande_array_dimlen[0][:2]
                    # reduces dimensionality to 3
                    array0_reshape = rec.ande_arrays[0].reshape(nx,ny,num_images)
                    imagenum = 0 # temporarily hardwired to image
                    plt.figure()
                    plt.imshow(array0_reshape[:,:,imagenum].T,origin="lower",extent=(rec.extent0[0],rec.extent0[1],rec.extent1[0],rec.extent1[1]))
                    plt.colorbar()
                    plt.xlabel("%s (%s)"%(rec.coord0,rec.units0))
                    plt.ylabel("%s (%s)"%(rec.coord1,rec.units1))
                    plt.title("%s: %s (%s)"%(recpath,rec.ampl_coord,rec.ampl_units))
                    pass
                pass
            pass
        pass
    plt.show()
    pass


