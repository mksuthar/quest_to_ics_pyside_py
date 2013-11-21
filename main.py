import sys
import random
import os
from PySide import QtGui, QtCore
from dateutil.parser import *
from dateutil.tz import *
from datetime import * 

# Dear future me, 
# I'm sorry.

class parser(object):
    """Parser object used to parse initial submission"""
    def __init__(self, container):
        super(parser, self).__init__()
        self.container = container
        self.list_of_courses = []
        self.all_event_list = []
        self.find_courses()

    # Parses course by splitting via "Exam Information"
    # as each course has exam information, in case there is inclusion of Online/PD
    # courses, then we need to split by Exam Schedule and material
    def find_courses(self):
        rough = [x.strip() for x in self.container.strip().split('Exam Information') if x != '']
        for i,x in enumerate(rough):
            if 'Exam Schedule' in x:
                rough += x.split('Exam Schedule\nMaterials')
                rough.pop(i)
        rough = [x for x in rough if x != '']
        
        for poss_co in rough:
            self.list_of_courses.append(Course(poss_co))
    
    def get_event_list(self):
        self.all_event_list = []
        # this is O(scary) to change later
        for x in self.list_of_courses:
            for y in x.component_list:
                for z in y.event_list:
                    self.all_event_list.append(z)
        return self.all_event_list


class Course(object):
    def __init__(self, container):
        super(Course, self).__init__()
        self.container = container.strip()
        self.component_list = []
        self.parse_and_identify()

    def parse_and_identify(self):
        fn =[x.strip() for x in self.container.split('\n')]
        fn = [x for x in fn if '\t' or '\n' not in x]
        self.id = fn[0]
        print(fn)
        l = []
        for i,x in enumerate(fn):
            if '\t' in x:
                l.append([i, len(x.split('\t'))])
                break
        
        print(l)
        l = l[0]
        g = fn[l[0]].split('\t')
        h = fn[l[0]+1:l[0]+l[1]+1]
        m = dict(zip(g, h))
        self.stripped_container = fn[l[0]+l[1]+2:]
        self.parse_and_create_components()
        
        
    def parse_and_create_components(self):
        g= self.stripped_container
        list_purge = []
        temp = 0
        
        for i,x in enumerate(self.stripped_container):
            if i > temp: 
                if len(x) > 0 and ',' == x.strip()[-1]:
                    for j,y in enumerate(self.stripped_container[i:]):
                        if len(y) == 0 or ',' != y.strip()[-1]:
                            list_purge.append([i,i+j])
                            temp = i+j
                            break

        if len(list_purge) > 0:
            for i,x in enumerate(list_purge):
                self.stripped_container[x[0]] = "".join(self.stripped_container[x[0]:x[1]+1])

            temp = self.stripped_container[:list_purge[0][0]+1]
            
            for i,x in enumerate(list_purge):
                if i == len(list_purge)-1:
                    break
                temp += self.stripped_container[x[1]+1:list_purge[i+1][1]]

            temp += self.stripped_container[list_purge[-1][1]+1:]
            self.stripped_container = temp

        identifier = self.stripped_container[0].split('\t')
        self.stripped_container = list(chunks(self.stripped_container[1:], len(self.stripped_container[0].split('\t'))))
        temp = self.stripped_container
        for i,x in enumerate(temp):
            if x[0] != '':
                self.component_list.append(component(x,identifier,self))
            else:
                self.get_last_comp().add_event(x,identifier)

    def get_last_comp(self):
        return self.component_list[-1]
    

def chunks(l, n):
    """ Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i+n]

def publish_cal():
    begin = '''
    BEGIN:VCALENDAR
    PRODID:-//hacksw/handcal//NONSGML v1.0//EN
    VERSION:2.0
    CALSCALE:GREGORIAN
    '''
    end = '''END:VCALENDAR'''


class component(object):
    def __init__(self, container, identifier,cc):
        super(component, self).__init__()
        self.cc = cc
        self.class_nbr = container[0]
        self.class_sec = container[1]
        self.class_com = container[2]
        self.event_list = []
        self.add_event(container, identifier)

    def add_event(self,container, identifier):
        self.event_list.append(event(self,dict(zip(identifier[3:],container[3:]))))

class event(object):
    def __init__(self, comp, container):
        super(event, self).__init__()
        self.comp = comp
        self.container = container

    def parse_code(self,inp):
        dic = {'$ccode': self.comp.cc.id.split('-')[0],
               '$cname': self.comp.cc.id.split('-')[-1],
                '$prof': self.container['Instructor'],
                '$room' : self.container['Room'],
                '$sec' : self.comp.class_sec,
                '$comp' : self.comp.class_com,
                '$classnum' : self.comp.class_nbr}

        for i, j in dic.items():
            inp = inp.replace(i, j)
        
        return inp


    def next_weekday(self,d, weekday):
        dic = {'MO':"0", 'TU':'1', 'WE':'2','TH':'3','FR':'4','SA':'5','SU':'6'}        
        for i, j in dic.items():
            if weekday == i:
                weekday = int(j)

        days_ahead = weekday - d.weekday()
        if days_ahead < 0: # Target day already happened this week
            days_ahead += 7
        a = d.date() + timedelta(days_ahead)
        return datetime.combine(a, datetime.min.time()) 

    def print_ics(self,summ,disc):
        jj = []
        start_date = 0;
        end_date = 0;
        days = []
        time = []

        vEvent = ''

        if len(self.container['Days & Times']) < 2 or self.container['Days & Times'] == 'TBA':
            return vEvent

        for i,v in enumerate(list(self.container.keys())):
            if v == 'Start/End Date':
                start_date = parse(self.container[v].split('-')[0].strip())
                end_date = parse(self.container[v].split('-')[-1].strip())

            if v == 'Days & Times':
                days = list(self.container[v].split(' ')[0].strip())
                for i,d in enumerate(days):
                    if d.upper() != d:
                        days[i-1] = days[i-1] + days[i].upper()
                days = [x for x in days if x == x.upper()] 
                print(self.container['Days & Times'])
                if len(self.container[v]) > 1 and self.container['Days & Times'] != 'TBA':
                    time = [self.container[v].split(' ')[1],self.container[v].split(' ')[3]]
        
        for i,x in enumerate(days):
            if x == 'M':
                days[i] = 'MO'
            elif x == 'T':
              days[i]  = 'TU'
            elif x == 'W':
              days[i]  = 'WE'
            elif x == 'TH':
             days[i]  = 'TH'
            elif x == 'F':
              days[i]  = 'FR'
            elif x == 'S':
              days[i]  = 'SA'
            elif x == 'S':
              days[i]  = 'SU'
            else:
                pass
        print(start_date,'<- be')
        start_date = self.next_weekday(start_date,days[0])
        print(start_date,'<- af')
        dtstart = parse(time[0],default=start_date)
        dtend = parse(time[1],default=start_date)
        until = parse(time[1],default=end_date)
        


        vEvent += '\n'+"BEGIN:VEVENT" + '\n'
        vEvent += "UID:"+  self.comp.cc.id + datetime.strftime(dtstart,'%S') + str(random.randint(1, 1000000)) + '-MK'+ '\n'
        vEvent += "DTSTAMP:" + datetime.strftime(datetime.now(), '%Y%m%dT%H%M%S') + '\n'
        vEvent += "DTSTART:" + datetime.strftime(dtstart, '%Y%m%dT%H%M%S') + '\n'
        vEvent += "SUMMARY:"+ self.parse_code(summ) + '\n'
        vEvent += "description".upper()+":" + self.parse_code(disc) + '\n'
        vEvent += "RRULE:FREQ=WEEKLY;UNTIL=" + datetime.strftime(until, '%Y%m%dT%H%M%S')+';WKST=SU;BYDAY=' + ','.join(days) + '\n'
        vEvent += "DTEND:"+datetime.strftime(dtend, '%Y%m%dT%H%M%S') + '\n'
        vEvent += "END:VEVENT" + '\n'
        return vEvent

class gui(QtGui.QWidget):

    def __init__(self):
        super(gui, self).__init__()
        self.initUI()
    
    def parse_and_save_cal(self):
        print(self.qwestCal.toPlainText())
        self.parse_engine = parser(self.qwestCal.toPlainText())
        summ = [self.combo1.currentText(),self.combo1.currentIndex()]
        disc = self.description.text()        
        if summ[1] == 0:
            summ = '$ccode'
        elif summ[1] == 1:
            summ = '$cname'
        elif summ[1] == 2:
            summ = '$ccode - $cname'
        else:
            summ = summ[0]

        dd = QtGui.QFileDialog.getSaveFileName()
        if dd[0].split('.') == '.ics':
            dd = dd[0].split('.')[0]
        else:
            dd = dd[0]

        with open(dd+'.ics', 'w') as f:
            f.write('BEGIN:VCALENDAR\nPRODID:-//hacksw/handcal//NONSGML v1.0//EN\nVERSION:1.0\nCALSCALE:GREGORIAN')
            for x in self.parse_engine.get_event_list():
                f.write(x.print_ics(summ,disc))
            f.write('END:VCALENDAR')


    def initUI(self):
        title = QtGui.QLabel('Qwest Cal to .ics parser')
        author = QtGui.QLabel('Version : 0.001')
        self.qwestCal = QtGui.QPlainTextEdit()
        btn = QtGui.QPushButton('Create Calendar', self)
        btn.clicked.connect(self.parse_and_save_cal)

        self.summary_label = QtGui.QLabel('Summary/Title :')
        self.combo1 = QtGui.QComboBox(self)
        self.combo1.addItem("Couse Code [ex: ENVE 224]")
        self.combo1.addItem("Course Name [ex: Probability & Statistics]")
        self.combo1.addItem("Course Code - CourseName [ex: ENVE 224 - Probability & Statistics]")
        self.description_label = QtGui.QLabel('Description : ')
        self.description_label_2 = QtGui.QLabel('use $room (Room No.), $prof (Instructo\'s name), $ccode (Couse Code), $cname (Couse Name), $sec (Section), $comp (Compnenet), $classnum (..)')
        self.description = QtGui.QLineEdit()
        self.combo1.setCurrentIndex(2)
        self.description.setText('$ccode ($comp) with $prof at $room')
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.summary_label)
        hbox.addWidget(self.combo1)
        hbox.addStretch(1)

        grid = QtGui.QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(title, 1, 0)
        grid.addWidget(author, 2, 0)
        grid.addWidget(self.qwestCal, 3, 0)
        grid.addLayout(hbox,4,0)
        grid.addWidget(self.description_label,5,0)
        grid.addWidget(self.description_label_2,6,0)
        grid.addWidget(self.description,7,0)
        grid.addWidget(btn, 8, 0)       
        self.setLayout(grid)

        self.setGeometry(300, 300, 350, 300)
        self.setWindowTitle('Quest Calendar Exporter')

        self.show()
 
def main():
    app = QtGui.QApplication(sys.argv)
    main_app = gui()
    sys.exit(app.exec_())
if __name__ == '__main__':
    main()
