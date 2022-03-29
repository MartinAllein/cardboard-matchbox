import sys
import os
import xml.dom.minidom
from abc import ABC, abstractmethod
import configparser

FILENAME = 'FILENAME'

TEMPLATE = 'TEMPLATE'


class Design(ABC):
    __DEFAULT_XML_LINE = '<line x1="%s" y1="%s"  x2="%s" y2="%s" />\n'
    __DEFAULT_XML_PATH = '<path d="M %s %s A %s %s 0 0 %s %s %s"/>\n'
    __DEFAULT_SECTION_NAME = "STANDARD"
    # __CONFIG_FILE = 'config/Design.config'
    __DEFAULT_CONFIG_FILE = "InsertMaker.config"
    __DEFAULT_X_ORIGIN = 0
    __DEFAULT_Y_ORIGIN = 0
    # Fallback settings when Design.config is missing
    __DEFAULT_X_OFFSET = 0
    __DEFAULT_Y_OFFSET = 0
    __DEFAULT_Y_LINE_SEPARATION = 7

    # Names for Configuration file elements
    __X_ORIGIN_NAME = "x origin"
    __Y_ORIGIN_NAME = "y origin"
    __X_OFFSET_NAME = "x offset"
    __Y_OFFSET_NAME = "y offset"
    __Y_LINE_SEPARATION_NAME = "y line separation"
    __UNIT_NAME = "unit"
    __XML_LINE_NAME = "xml line"
    __XML_PATH_NAME = "xml path"

    __UNIT_MM_TEXT = 'mm'
    __UNIT_MIL_TEXT = 'mil'
    __DEFAULT_UNIT = __UNIT_MM_TEXT

    xml_line = __DEFAULT_XML_LINE
    xml_path = __DEFAULT_XML_PATH
    x_origin = __DEFAULT_X_ORIGIN
    y_origin = __DEFAULT_Y_ORIGIN
    x_offset = __DEFAULT_X_OFFSET
    y_offset = __DEFAULT_Y_OFFSET
    y_line_separation = __DEFAULT_Y_LINE_SEPARATION
    unit_mm = True

    # Line Types
    LINE = "Line"
    THUMBHOLE = "Path"
    HALFCIRCLE = "Halfcircle"
    QUARTERCIRCLE = "Quartercircle"
    PAIR = "Pair"

    # Drawing directions
    SOUTH = "South"
    NORTH = "North"
    EAST = "East"
    WEST = "West"
    VERTICAL = "Vertical"
    HORIZONTAL = "Horizontal"
    CW = 1
    CCW = 0

    FACTOR = 720000 / 25.4
    __default_configuration = {}

    @abstractmethod
    def create(self):
        pass

    @abstractmethod
    def parse_arguments(self):
        pass

    @staticmethod
    def __divide_dpi(coord: str):
        if coord == 0:
            value = "00000"
        else:
            value = str(coord)

        return value[:-4] + "." + value[-4:]

    @staticmethod
    def thoudpi_to_dpi(coord):

        if type(coord) is list:
            result = []
            for item in coord:
                result.append(Design.__divide_dpi(item))
        else:
            result = Design.__divide_dpi(coord)
        return result

    @staticmethod
    def draw_line(start, end):
        start_x, start_y = Design.thoudpi_to_dpi(start)
        end_x, end_y = Design.thoudpi_to_dpi(end)
        return Design.__DEFAULT_XML_LINE % (start_x, start_y, end_x, end_y)

    @staticmethod
    def draw_halfcircle(corners, path):
        start_x, start_y = corners[path[0]]
        end_x, end_y = corners[path[1]]
        orientation = path[2]

        diameter = 0
        if orientation == Design.VERTICAL:
            diameter = abs(end_y - start_y)
        else:
            diameter = abs(end_x - start_x)

        return Design.__draw_arc(start_x, start_y, int(diameter / 2), Design.CW, end_x, end_y)

    def draw_quartercircle(corners, path):
        start_x, start_y = corners[path[0]]
        end_x, end_y = corners[path[1]]
        orientation = path[2]

        diameter = 0
        if orientation == Design.VERTICAL:
            radius = abs(end_y - start_y)
        else:
            radius = abs(end_x - start_x)

        return Design.__draw_arc(start_x, start_y, int(radius), Design.CW, end_x, end_y)

    @staticmethod
    def draw_thumbhole_path(corners, path):
        start_x, start_y = corners[path[0]]
        smallradius, thumbholeradius, direction, orientation = path[1:]

        delta = {
            Design.NORTH: [[-smallradius, -smallradius, direction], [0, -2 * thumbholeradius, 1 - direction],
                           [smallradius, -smallradius, direction]],
            Design.SOUTH: [[smallradius, smallradius, direction], [0, 2 * thumbholeradius, 1 - direction],
                           [-smallradius, smallradius, direction]],
            Design.WEST: [[-smallradius, -smallradius, 1 - direction], [-2 * thumbholeradius, 0, direction],
                          [-smallradius, +smallradius, 1 - direction]],
            Design.EAST: [[smallradius, smallradius, 1 - direction], [2 * thumbholeradius, 0, direction],
                          [smallradius, -smallradius, 1 - direction]],
        }

        xmlstring = ""
        for values in delta[orientation]:
            end_x = start_x + values[0]
            end_y = start_y + values[1]
            outstring = Design.__draw_arc(start_x, start_y, smallradius, values[2], end_x, end_y)
            xmlstring += outstring
            start_x = end_x
            start_y = end_y

        return xmlstring

    @staticmethod
    def __draw_arc(start_x, start_y, radius, direction, end_x, end_y):
        return Design.__DEFAULT_XML_PATH % (
            Design.thoudpi_to_dpi(start_x), Design.thoudpi_to_dpi(start_y), Design.thoudpi_to_dpi(radius),
            Design.thoudpi_to_dpi(radius), direction, Design.thoudpi_to_dpi(end_x), Design.thoudpi_to_dpi(end_y))

    @staticmethod
    def draw_lines(corners, lines):
        xml_lines = ""
        for command, values in lines:
            if command == Design.LINE:
                for start, end in zip(values[:-1], values[1:]):
                    xml_lines += Design.draw_line(corners[start], corners[end])
            elif command == Design.THUMBHOLE:
                xml_lines += Design.draw_thumbhole_path(corners, values)
            elif command == Design.PAIR:
                for start, end in zip(values[::2], values[1::2]):
                    xml_lines += Design.draw_line(corners[start], corners[end])
            elif command == Design.HALFCIRCLE:
                xml_lines += Design.draw_halfcircle(corners, values)
            elif command == Design.QUARTERCIRCLE:
                xml_lines += Design.draw_quartercircle(corners, values)

        return xml_lines

    @staticmethod
    def get_bounds(corners):

        left_x = min(a for (a, b) in corners)
        top_y = min(b for (a, b) in corners)
        right_x = max(a for (a, b) in corners)
        bottom_y = max(b for (a, b) in corners)

        return left_x, right_x, top_y, bottom_y

    @staticmethod
    def write_to_file(items):

        if FILENAME not in items:
            raise "No filename given"

        if TEMPLATE not in items:
            raise " No tamplate given"

        if not os.path.isfile(items[TEMPLATE]):
            raise "Template file does not exist"

        with open(items[TEMPLATE], 'r') as f:
            template = f.read()

        # modify FILENAME with leading and trailing $
        items["$FILENAME$"] = items[FILENAME]
        filename = items[FILENAME]
        del items[FILENAME]

        for key in items:
            template = template.replace(key, str(items[key]))

        dom = xml.dom.minidom.parseString(template)
        template = dom.toprettyxml(newl='')

        with open(f"{filename}", 'w') as f:
            f.write(template)

    @staticmethod
    def read_template(template: str):
        string = ""
        if not template:
            raise "No template name given"

        if not os.path.isfile('templates/' + template):
            raise "Template file does not exist"

        with open("templates/" + template, 'r') as f:
            string = f.read()

        return string

    @staticmethod
    def thoudpi_to_mm(value):
        return round(value / Design.FACTOR, 2)

    @staticmethod
    def mm_to_thoudpi(value):
        return int(float(value) * Design.FACTOR)

    def foobar(self):
        pass

    @staticmethod
    def read_config(filename, section=None, defaults=None):
        print(filename[-7:])

        if filename[-7:] != ".config":
            filename += ".config"

        filename = 'config/' + filename
        # Read default values from the config file
        if not os.path.isfile(filename):
            print("Config file " + filename + " not found")
            sys.exit()

        # read entries from the configuration file
        configuration = configparser.RawConfigParser(defaults=defaults)
        configuration.read(filename)

        if section:
            if not configuration.has_section(section):
                print("Section " + section + " in config file " + filename + " not found")
                sys.exit()

        return configuration

    @classmethod
    def default_config(cls):
        defaults = {cls.__X_ORIGIN_NAME: 0,
                    cls.__Y_ORIGIN_NAME: 0,
                    cls.__X_OFFSET_NAME: 0,
                    cls.__Y_OFFSET_NAME: 0,
                    cls.__Y_LINE_SEPARATION_NAME: cls.__DEFAULT_Y_LINE_SEPARATION,
                    cls.__XML_LINE_NAME: cls.__DEFAULT_XML_LINE,
                    cls.__XML_PATH_NAME: cls.__DEFAULT_XML_PATH,
                    cls.__UNIT_NAME: cls.__DEFAULT_UNIT
                    }

        configuration = cls.read_config(filename=cls.__DEFAULT_CONFIG_FILE, section=cls.__DEFAULT_SECTION_NAME,
                                        defaults=defaults)

        cls.x_origin = int(configuration.get(cls.__DEFAULT_SECTION_NAME, cls.__X_ORIGIN_NAME))
        cls.y_origin = int(configuration.get(cls.__DEFAULT_SECTION_NAME, cls.__Y_ORIGIN_NAME))
        cls.x_offset = int(configuration.get(cls.__DEFAULT_SECTION_NAME, cls.__X_OFFSET_NAME))
        cls.y_offset = int(configuration.get(cls.__DEFAULT_SECTION_NAME, cls.__Y_OFFSET_NAME))
        cls.y_line_separation = int(configuration.get(cls.__DEFAULT_SECTION_NAME, cls.__Y_LINE_SEPARATION_NAME))
        cls.xml_line = configuration.get(cls.__DEFAULT_SECTION_NAME, cls.__XML_LINE_NAME)
        cls.xml_line = configuration.get(cls.__DEFAULT_SECTION_NAME, cls.__XML_LINE_NAME)

        if configuration[cls.__DEFAULT_SECTION_NAME][cls.__UNIT_NAME] == cls.__UNIT_MIL_TEXT:
            cls.unit_mm = False


Design.default_config()
print(Design.x_origin)
print(Design.y_origin)
print(Design.x_offset)
print(Design.y_offset)
print(Design.xml_line)
print(Design.xml_path)
print(Design.y_line_separation)
print(Design.unit_mm)
