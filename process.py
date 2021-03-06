#!/usr/local/bin/managed_python3

"""
CLI Application to streamline the creation of PKGInfo files 
for printer deployment in Munki. 

Created by Tim Schutt for Syracuse University, 2014 - taschutt@syr.edu
Bug squashing assistance from Vaughn Miller

Much code reused from Printer PKG deploy scripts by:
Walter Meyer, SUNY Purchase, 2010
Nick McSpadden, 2013
"""

import os, sys, subprocess, shlex, string, re, plistlib
from optparse import Option

dirname,filename = os.path.split(os.path.abspath(__file__))
os.chdir(dirname)

## Modify the following to match your environment. 
## These are used to set driver dependencies. 
## The dictionary is configured as 'Human readable':'munki pkgname'

driverCollection = {'Hewlett Packard':'HewlettPackardPrinterDrivers',\
                    'RICOH':'RicohPrinterDrivers',\
                    'Xerox':'XeroxPrinterDrivers',\
                    'Canon':'CanonPrinterDrivers'}  

## Enter an example of your house naming convention

nameExample = "p1-loc.build.lafayette"

## defining variables so fnPrintCurrentState doesn't bark at me
## before they are populated.
printers = []
selectedPrinter = ""
DeviceURI = ""
SelectedPPD = ""
PrinterDriver = ""
OptionList = []
PkgInfoName = ""

def fnPrintCurrentState():
    """prints current state of script to user - showing
    discovered and selected values."""
    
    #os.system('clear')
    print("=============================\n")
    print("Selected Printer     :", Printer)
    
    if (DeviceURI):
        print("Printer URI          :", DeviceURI)
        print("Printer Display Name :", PrinterDisplayName)
        print("Printer Make & Model :", PrinterMakeModel)
        print("Printer Location     :", PrinterLocation)
        
    if (DeviceURI[:6] == "smb://"):
        print("\nPrinter Connection   : Active Directory Queue")
        print("Print Server         :", PrintServer)
        print("Printer Queue        :", PrinterQueue)
    else:
        print("\nPrinter Connection   : Direct")
    
    if (SelectedPPD):
        print("\nPPD Selected         :", SelectedPPD)
        
    if (PrinterDriver):
        print("Selected Drivers     :", PrinterDriver)
            
    if (OptionList):
        x = False
        print("\nSelected Options     :",)
        
        for eachoption in OptionList:
            if (x):
                print("                     :", eachoption)
            else:
                print(eachoption)
                x = True
    if (PkgInfoName):
        print("\nDeployment Name      :", PkgInfoName)
        print("Deployment Version   :", PkgInfoVersion)            
    print("\n=============================\n")

def fnGetConfiguredPrinter():
    """lists currently installed and configured printers on the system
    where the script is running."""
    
    if (len(printers) > 0):
        del printers [:]

    printersList = subprocess.run(['/usr/bin/lpstat', '-p'], stdout=subprocess.PIPE).stdout.decode('utf-8').splitlines()        

    for printerLine in printersList:
        if printerLine.count(' ') > 1:
            printerElements = printerLine.split()
            if printerElements[0] == 'printer':
                printers.append(printerElements.pop(1))
    
    fnChooseConfiguredPrinter(printers)

def fnChooseConfiguredPrinter(printers):
    """ creates enumerated list of printers for user to select for deployment."""
    
    #os.system('clear')

    print("\tPlease select the printer you wish to deploy.\n")
    
    for prnIndex, printer in enumerate(printers):
        print('\t[', prnIndex+1, ']', printer)   #enumerate starting with 1   
    
    printerSelection = (int(input('\n\n\tChoice: '))-1)  #subtract 1 from response
    
    ### check input here - TBD ###
    
    #os.system('clear')
    fnPrnSelVerify(printers[int(printerSelection)])
   
def fnPrnSelVerify(selectedPrinter):
    """verify correct printer selection prior to continuing, and 
    give user option to reselect. """
    
    print('\n\tYou selected: ', selectedPrinter, "\n\n")
    
    x = input("\tIs this correct? [y or n]: ")
       
    if str(x) == "n":
        fnChooseConfiguredPrinter(printers)
    elif str(x) == "y":
        global Printer
        Printer = selectedPrinter
    else:
        #os.system('clear')
        print("I'm sorry, I didn't understand that.")
        fnPrnSelVerify(selectedPrinter)

def fnGetDeviceInformation(SelPrinter):
    optionsRawList = subprocess.run(['/usr/bin/lpoptions', '-p', SelPrinter], stdout=subprocess.PIPE).stdout.decode('utf-8').split()
    
    OptionsList = {}
    
    for ov in optionsRawList:
        if "=" in ov:
            ovDictLoad = ov.split("=")
            OptionsList[ovDictLoad[0]] = str(ovDictLoad[1])
    
    global DeviceURI 
    DeviceURI = OptionsList['device-uri']
    global PrinterDisplayName
    PrinterDisplayName = OptionsList['printer-info']
    global PrinterMakeModel 
    PrinterMakeModel = OptionsList['printer-make-and-model']
    global PrinterLocation
    try: 
        PrinterLocation = OptionsList['printer-location']
    except:
        PrinterLocation = ""
    
    if (DeviceURI[:6] == "smb://"):
        global PrintServer
        global PrinterQueue
        matched = re.match(r"(smb:\/\/[\w\-\.]+)\/(.+)", DeviceURI)
        PrintServer = matched.group(1)
        PrinterQueue = matched.group(2)
        
def fnChoosePPD():
    """prompts for search term, and shows matching contents from 
    /Library/Printers/PPDs/Contents/Resources for PPD selection."""
    
    fnPrintCurrentState()
    print("What PPD would you like to use with this printer?\n")
    print("Enter a search term for the PPD. Usually, a model number works well when ")
    print("attempting to select a PPD, so if you have an HP M401dne, try 'M401', or  ")
    print("for a Canon ImageRunner Advance 6075 copier, try simply '6075'.")
    
    ppdSearchTerm = input('Search Term: ')
    
    if (len(ppdSearchTerm) < 1):
        fnChoosePPD()

    ppdListRaw = subprocess.run(['/usr/sbin/lpinfo', '-m'], stdout=subprocess.PIPE).stdout.decode('utf-8').splitlines()
    print(ppdListRaw)
    ppdList = []
    for ppd in ppdListRaw:
        if ppd.startswith('drv'):
            ppdList.append(ppd.split(' ', 1)[0])
        if ppd.startswith('Library'):
            ppdList.append('/' + ppd.split('gz ', 1)[0] + 'gz')
    
    foundPPDs = []
    
    for ppd in ppdList:
        if str(ppdSearchTerm) in ppd:
            foundPPDs.append(ppd)
            
    fnPrintCurrentState()
    
    if (len(foundPPDs) < 1):
        print("I'm sorry - I couldn't find anything.")
        print("Do you have the drivers installed on this system?")
        junk = input("Press [Enter] to retry.")
        fnChoosePPD()
    else:  
        print("I found the following PPDs that might work - enter the number")
        print("of the one you would like to use, or '9999' to search again.")  
        for ppdIndex, ppdSuggest in enumerate(foundPPDs):
            print("[",ppdIndex+1,"] -", ppdSuggest)
        print("[ 9999 ] - Search Again\n")
        print("# of found PPDs:", len(foundPPDs))
        
        ppdSelectIndex = (int(input('Selection: '))-1)
        
        if ppdSelectIndex == "9998":
            print("OK - restarting search")
            fnChoosePPD()
        elif (ppdSelectIndex >= 0) & (ppdSelectIndex < int(len(foundPPDs))):
            global SelectedPPD
            SelectedPPD = foundPPDs[int(ppdSelectIndex)]
            print("You selected ", SelectedPPD)
        else:
            print("!!! ERROR, Will Robinson - I don't have that in my list !!!\n\n")
            fnChoosePPD()

def fnSetPackageDependancy(driverCollection):
    """Displays driver packages available via munki repo - dictionary
    is populated in script configuration above. Will set user selection
    as a dependant installation in the pkginfo file."""
    
    print("These are the driver sets available in the Munki repository.")
    print("Please select which set is required by this printer, or if")
    print("you will install the drivers by hand.\n")
    
    printerStyles = []
    driverSets = []
    
    printerStyles = sorted(driverCollection)
    
    for listIndex, printerStyle in enumerate(printerStyles):
        driverSets.append(driverCollection[printerStyle])
        print('[',listIndex+1,'] -', printerStyle)
    print("[9999] - No Dependency, will install by hand.")
    
    driverSelect = (int(input('Selection: '))-1)
    
    global PrinterDriver
    
    if (driverSelect == 9998):
        PrinterDriver = ''
    elif ((driverSelect >= 0) & (driverSelect < len(driverSets))):
        PrinterDriver = driverSets[driverSelect]
    else:
        print("I'm sorry, I didn't understand that input. Please try again")
        fnSetPackageDependancy()
        
def fnSetPrinterOptions():
    """reads complete list of printer options via lpoptions -l. Parses them
    to a list of 'option=value' suitable for inclusion in the printer creation 
    (lpadmin) command below. User can select from the list with a collection of 
    comma separated values."""
    
    cmdGetOpts = ['lpoptions', '-p', Printer, '-l']
    resultGetOpts = subprocess.run(cmdGetOpts, stdout=subprocess.PIPE).stdout.decode('utf-8')    
    resultLinesGetOpts = resultGetOpts.splitlines()
    
    global OptionList
    OptionList = []
    printerOptionsDict = {}
    printerOptions = []

    for option in resultLinesGetOpts:
        if len(option) > 3:
            optionSet = option.split(':')
            tempKey = optionSet[0]
            tOK = tempKey.split("/")
            oK = tOK[0]
            query = re.compile('\*\w+')
            optResult = query.findall(optionSet[1])
            oV = optResult[0]
            printerOptionsDict[oK] = oV    

    print(printerOptionsDict)
    for printerOption in printerOptionsDict:
        print(printerOption + ' : ', printerOptionsDict[printerOption])
        printerOptions.append(printerOption + "=" + printerOptionsDict[printerOption])
        
    for number, option in enumerate(printerOptions):
        print("[", number+1, "] ", option)
        
    optionSelect = str(input('Please enter the options you would like to include, separated by commas. : '))
    
    if (len(optionSelect) > 0):
        for s in optionSelect.split(','):
            selection = int(s)-1
            OptionList.append(printerOptions[selection])
        
    if (DeviceURI[:6] == "smb://"):
        OptionList.append('printer-op-policy=authenticated')
    
    OptionList.append('printer-is-shared=False')
    OptionList.append('printer-error-policy=abort-job')
        
def fnVerifySelections(retry):
    """Ensure that all selected values for printer, options, PPD and dependancies
    are correct. If so, prompt for deployment name (with suggested naming convention)
    and if not, restart the process"""
    
    if (retry):
        print("\tI'm sorry, I didn't understand that response.\
        \n\tPlease enter 'y' or 'n'.")
    
    verified = str(input('\tAre these settings correct? [y/n]: '))
    
    if verified == 'y':  #start prompting for printer name, version and description
        fnPrintCurrentState()
        global PkgInfoName
        global PkgInfoDescription
        global PkgInfoVersion
        PkgInfoName = str(input('\tPlease enter the deployment name.\
        \n\tExample: ' + nameExample + '\n\t>>> '))
        PkgInfoDescription = str(input('\n\tPlease enter a printer description.\n\t>>> '))
        PkgInfoVersion = str(input('\n\tPlease enter the deployment version: '))
    elif verified == 'n':
        printerSelection = fnGetConfiguredPrinter()
    else:
        fnPrintCurrentState()
        fnVerifySelections(True)

def fnBuildInstallCommand():
    """pull together all selections into appropriate lpadmin printer creation
    command."""
    
    global InstallCommand
    printerDisplayNameQuoted = '"%s"' % (PrinterDisplayName)
    printerLocationQuoted = '"%s"' % (PrinterLocation)
    SelectedPPDQuoted = '"%s"' % (SelectedPPD)

    
    InstallCommandParts = ['/usr/sbin/lpadmin', '-E', '-p', Printer, \
                           '-L', printerLocationQuoted, '-D', \
                           printerDisplayNameQuoted]

    
    # Slightly different options depending on type of PPD
    if SelectedPPD.endswith('.gz'):      # An installed driver
        InstallCommandParts.append('-P')                       
        InstallCommandParts.append(SelectedPPDQuoted)
    if SelectedPPD.endswith('.ppd'):    # Built in generic driver
        InstallCommandParts.append('-m')
        InstallCommandParts.append(SelectedPPDQuoted)

    InstallCommandParts.append('-v')
    InstallCommandParts.append(DeviceURI)
    
    for opt in OptionList:  #iterates through option list selections
        InstallCommandParts.append('-o')
        InstallCommandParts.append(opt)
    
    InstallCommand = ' '.join(InstallCommandParts) #collapses it all into one nice string
           
def fnModifyScripts():
    """Reads in template installcheck, postinstall and uninstall scripts,
    replacing tagged sections with generated content and commands. Writes
    them out to temporary files in the same directory as the python script."""
    
    with open("installcheck_script.sh", "wt") as fout:
        with open("supportFiles/installcheck_script.sh", "rt") as fin:
            for line in fin:
                line = line.replace("<version>", PkgInfoVersion)
                line = line.replace("<printername>", Printer)
                fout.write(line)
    
    with open("postinstall_script.sh", "wt") as fout:
        with open("supportFiles/postinstall_script.sh", "rt") as fin:
            for line in fin:
                line = line.replace("<version>", PkgInfoVersion)
                line = line.replace("<printername>", Printer)
                line = line.replace("<installcommand>", InstallCommand)
                fout.write(line)
                
    with open("uninstall_script.sh", "wt") as fout:
        with open("supportFiles/uninstall_script.sh", "rt") as fin:
            for line in fin:
                line = line.replace("<printername>", Printer)
                fout.write(line)
                
    fnMakePkgInfo() #calls the MakePkgInfo
    
    cmdCleanup = ['rm', 'installcheck_script.sh', \
                  'postinstall_script.sh', 'uninstall_script.sh']
    subprocess.call(cmdCleanup) # deletes temporary script files.
                
def fnMakePkgInfo():
    """Builds and executes the makepkginfo command utilizing the install scripts
    generated in fnModifyScripts. Collects output into variable."""
    
    pkgVers = '--pkgvers=' + PkgInfoVersion
    printerDisplayName = '--displayname=' + PrinterMakeModel + ', ' + PrinterLocation
    printerDescription = '--description=' + PkgInfoDescription
    pkgInfoFileName = PkgInfoName + '-' + PkgInfoVersion + '.plist'

    makePkgInfoCMD = ['/usr/local/munki/makepkginfo', '--unattended_install', \
                      '--uninstall_method=uninstall_script', \
                      '--name=' + PkgInfoName, printerDisplayName, printerDescription, \
                      '--nopkg', '--installcheck_script=installcheck_script.sh', \
                      '--postinstall_script=postinstall_script.sh', \
                      '--uninstall_script=uninstall_script.sh', \
                      '--minimum_os_version=10.6.8', pkgVers, \
                      "--category=Printers"]
    # Only add the 'requires' key if PrinterDriver has a value
    if PrinterDriver != '':
        makePkgInfoCMD.append('-r')
        makePkgInfoCMD.append(PrinterDriver)        
        
    pkginfoResult = subprocess.run(makePkgInfoCMD, stdout=subprocess.PIPE).stdout.decode('utf-8')

    with open(pkgInfoFileName, "wt") as pkgout: #writes variable output to file.
        for line in pkginfoResult:
            pkgout.write(line)
            
    ### Now we add the uninstallable key
    
    with open(pkgInfoFileName, 'rb') as fp:
        plistInput = plistlib.load(fp)

    plistInput["uninstallable"] = True
 
    with open(pkgInfoFileName, 'wb') as fp:
        plistlib.dump(plistInput, fp)
    
    print("PkgInfo printer deployment file has been created as " + pkgInfoFileName)
 
###
#  Kick the whole damn thing off
###    
printerSelection = fnGetConfiguredPrinter()
fnPrintCurrentState()
fnGetDeviceInformation(Printer)
fnPrintCurrentState()
fnChoosePPD()
fnPrintCurrentState()
fnSetPackageDependancy(driverCollection)
fnPrintCurrentState()
fnSetPrinterOptions()
fnPrintCurrentState()
fnVerifySelections(False)
fnPrintCurrentState()
fnBuildInstallCommand()
fnModifyScripts()