from re import compile, search, sub
from lib.log import log
from time import sleep


class Interpreter():
    def __init__(self, X, C, Z, parallelport, kss):
        self.X = X
        self.C = C
        self.Z = Z

        self.kss = kss
        self.pport = parallelport
        self.variables = {}


    def gcode_clean(self, gcode):
        clean = []
        for line in gcode:
            line_clean = self.comment_remove(line)
            if line_clean:
                clean.append(line_clean)
        return clean

    def comment_remove(self, gcode):
        gcode = sub('\(.*\)', '', gcode)
        gcode = gcode.split(';')[0]
        gcode = sub(' +', ' ', gcode)
        return gcode.strip()

    def process(self, gcode):
        log('Bereinige G-Code')
        gcode = self.gcode_clean(gcode)
        self.m30 = False

        log('Motorstatus:')
        log('X: \033[96m{0:b}\033[0m'.format(self.X.status()))
        #log('C: \033[96m{0:b}\033[0m'.format(self.C.status()))
        log('Z: \033[96m{0:b}\033[0m'.format(self.Z.status()))

        log('Starte G-Code')
        for line in gcode:
            self.line_process(line)

    def line_process(self, line):
        log('Bearbeite G-Code Befehl: {0}'.format(line))
        if self.m30 == True:
            log('Programmende erreicht! Befehl: {0} wird nicht mehr ausgefuehrt!'.format(line))
            return

        if line[0] == '#':
            line = line.split()
            self.variables[line[0]] = line[2]
            log('Variable {0} mit Wert {1} gespeichert'.format(line[0], self.variables[line[0]]))
        elif line == 'G54':
            log('Setze Koordinatensystem G54')
            self.X.offset = self.kss['G54'].x_offset
            self.X.inverted = self.kss['G54'].x_inverted
            self.Z.offset = self.kss['G54'].z_offset
            self.Z.inverted = self.kss['G54'].z_inverted
        elif line == 'G61':
            log('Exact Path Mode')
        elif line == 'T1':
            log('Tool T1 ausgewaehlt')
        elif line == 'M30':
            log('Programmende erreicht')
            self.m30 = True
        elif line == 'M100':
            log('Spindel ein')
            # C.rotate()
        # elif line == 'M101':
        #     log('Spindel verlangsamen')
        #     raw_input('Das macht eigentlich keinen Sinn mehr')
        #     # C.rotate(C.umin_default / 2)
        elif line == 'M102':
            log('Spindel aus')
            # C.stop()
            # C.wait()
        elif line == 'M103':
            log('Bereitschaftssignal aus!')
            self.pport.setPin(14, False)
        elif line == 'M104':
            log('In Home Position fahren und Bereitschaftssignal ein')
            self.X.move_abs(0)
            self.Z.move_abs(0)
            self.X.wait()
            self.Z.wait()
            raw_input('Hier wird kein Sleep durchgefueht, da auf Achsen gewartet wird!')
            # log('Sleep 1.0s')
            # sleep(1)
            log('Pin 10: {0}'.format(self.pport.getPin(10))) # False -> X in Home-Position
            log('Pin 12: {0}'.format(self.pport.getPin(12))) # False -> Z in Home-Position
            if self.pport.getPin(10) == False and self.pport.getPin(12) == False:
                self.pport.setPin(14, True)
            else:
                self.pport.setPin(14, False)
                raise ValueError('Maschine befindet sich nicht in Home-Position!')
        elif line == 'M115':
            log('Greifer 8 schliessen')
            self.pport.setPin(9, True)
        elif line == 'M116':
            log('Greifer 8 oeffnen')
            self.pport.setPin(9, False)
        elif line[0:2] == 'G4':
            time = search('(?<=P)[0-9\.]*$', line).group(0)
            log('{0} Sekunden Verweilzeit'.format(time))
            sleep(float(time))
        elif line.split()[0] == 'G01':
            self.x = None
            self.z = None
            self.speed = None
            commands = line.split()[1:]
            for command in commands:
                if command[0] == 'X':
                    position = command[1:]
                    if self.is_float(position):
                        self.x = float(position)
                    else:
                        position = position[1:-1]
                        pattern = compile('|'.join(self.variables.keys()))
                        position = pattern.sub(lambda x: self.variables[x.group()], position)
                        try:
                            self.x = eval(position)
                        except:
                            raise ValueError('111 G-Code Kommando unbekannt: {0}'.format(command))
                elif command[0] == 'Z':
                    position = command[1:]
                    if self.is_float(position):
                        self.z = float(position)
                    else:
                        position = position[1:-1]
                        pattern = compile('|'.join(self.variables.keys()))
                        position = pattern.sub(lambda x: self.variables[x.group()], position)
                        try:
                            self.z = eval(position)
                        except:
                            raise ValueError('222 G-Code Kommando unbekannt: {0}'.format(command))
                elif command[0] == 'F':
                    speed = command[1:]
                    if self.is_float(speed):
                        self.speed = float(speed)
                    else:
                        speed = speed[1:-1]
                        pattern = compile('|'.join(self.variables.keys()))
                        speed = pattern.sub(lambda x: self.variables[x.group()], speed)
                        try:
                            self.speed = eval(speed)
                        except:
                            raise ValueError('333 G-Code Kommando unbekannt: {0}'.format(command))
                else:
                    raise ValueError('444 G-Code Kommando unbekannt: {0}'.format(line))


            if self.x != None and self.z != None:
                log('Moving to X: {0}, Z: {1} with speed: {2}'.format(self.x, self.z, self.speed))
                log('ACHTUNG! Es wird aktuell jede Achse mit der angegebenen Geschwindigkeit verfahren!')
                #raw_input('Fortfahren?')
                self.X.move_abs(self.x, self.speed)
                self.Z.move_abs(self.z, self.speed)
            elif self.x != None:
                log('Moving to X: {0} with speed: {1}'.format(self.x, self.speed))
                self.X.move_abs(self.x, self.speed)
            elif self.z != None:
                log('Moving to Z: {0} with speed: {1}'.format(self.z, self.speed))
                self.Z.move_abs(self.z, self.speed)
            else:
                raise ValueError('555 G-Code Kommando unbekannt: {0}'.format(line))
            self.X.wait()
            self.Z.wait()
        else:
            raise ValueError('666 G-Code Kommando unbekannt: {0}'.format(line))

    def is_float(self, string):
        try:
            float(string)
        except ValueError:
            return False
        return True
