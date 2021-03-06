from re import compile, search, sub
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
        print 'Bereinige G-Code'
        gcode = self.gcode_clean(gcode)
        self.m30 = False

        print 'Motorstatus:'
        print 'X: \033[96m{0:b}\033[0m'.format(self.X.status())
        print 'C: \033[96m{0:b}\033[0m'.format(self.C.status())
        print 'Z: \033[96m{0:b}\033[0m'.format(self.Z.status())

        print 'Starte G-Code'
        for line in gcode:
            self.line_process(line)

    def line_process(self, line):
        print 'Bearbeite G-Code Befehl: {0}'.format(line)
        if self.m30 == True:
            print 'Programmende erreicht! Befehl: {0} wird nicht mehr ausgefuehrt!'.format(line)
            return

        if line[0] == '#':
            line = line.split()
            self.variables[line[0]] = line[2]
            print 'Variable {0} mit Wert {1} gespeichert'.format(line[0], self.variables[line[0]])
        elif line == 'G54':
            print 'Setze Koordinatensystem G54'
            self.X.offset = self.kss['G54'].x_offset
            self.X.inverted = self.kss['G54'].x_inverted
            self.Z.offset = self.kss['G54'].z_offset
            self.Z.inverted = self.kss['G54'].z_inverted
        elif line == 'G61':
            print 'Exact Path Mode'
        elif line == 'T1':
            print 'Tool T1 ausgewaehlt'
        elif line == 'M30':
            print 'Programmende erreicht'
            self.m30 = True
        elif line == 'M100':
            print 'Spindel ein'
            self.C.rotate(300)
        elif line == 'M102':
            print 'Spindel aus'
            self.C.stop()
            self.C.wait()
        elif line == 'M103':
            print 'Bereitschaftssignal aus!'
            self.pport.setPin(14, False)
        elif line == 'M104':
            print 'In Home Position fahren und Bereitschaftssignal ein'
            self.Z.move_abs(0)
            self.X.move_abs(0)
            self.Z.wait()
            self.X.wait()
            print 'Pin 10: {0}'.format(self.pport.getPin(10)) # False -> X in Home-Position
            print 'Pin 12: {0}'.format(self.pport.getPin(12)) # False -> Z in Home-Position
            self.pport.setPin(14, True)
        elif line == 'M115':
            print 'Greifer 8 schliessen'
            self.pport.setPin(9, True)
        elif line == 'M116':
            print 'Greifer 8 oeffnen'
            self.pport.setPin(9, False)
        elif line[0:2] == 'G4':
            time = search('(?<=P)[0-9\.]*$', line).group(0)
            print '{0} Sekunden Verweilzeit'.format(time)
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
                delta_x = abs(self.x - self.X.get_position())
                delta_z = abs(self.z - self.Z.get_position())
                ratio = delta_z / float(delta_x)
                speed_x = self.speed / (1+ratio**2)**0.5
                speed_z = speed_x * ratio
                print 'Moving to X: {0} with speed {1}'.format(self.x, speed_x)
                print 'Moving to Z: {0} with speed {1}'.format(self.z, speed_z)
                self.X.move_abs(self.x, self.speed)
                self.Z.move_abs(self.z, self.speed)
            elif self.x != None:
                print 'Moving to X: {0} with speed: {1}'.format(self.x, self.speed)
                self.X.move_abs(self.x, self.speed)
            elif self.z != None:
                print 'Moving to Z: {0} with speed: {1}'.format(self.z, self.speed)
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
