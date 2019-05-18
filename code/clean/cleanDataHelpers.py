import re
# used to check the subject[subjectScheme] payload to determine whether this is
# a dewey decimal subject
ddcNames = [
        "Dewey decimal Classification",
        "Dewey-Dezimalklassifikation (DDC) (http://ddc-deutsch.de/)",
        "DeweyDecimalClassification",
        "dewey",
        "ddccode",
        "ddc",
        "Dewey Classification"
            " (http://opac.bncf.firenze.sbn.it/opac/controller.jsp"
            "?action=dewey_browse&deweypath_cod=9)",
        "DDC (Dewey-Dezimalklassifikation) (http://www.ddc-deutsch.de)",
        "DDC"]

# Used to map the payload (subject["value"]) of a DDC-subject to the base classes
# of ANZSRC. Unhandled DDC classes:
#  ^03[^.] | Encyclopedias & books of facts
#  ^04[^.] | Unassigned (formerly Biographies)
#  ^05[^.] | Magazines, journals & serials
#  ^06[^.] | Associations, organizations & museums
#  ^08[^.] | Quotations
#  ^09[^.] | Manuscripts & rare books
#  ^35[^.] | Public administration & military science
#  ^39[^.] | Customs, etiquette, & folklore
#  ^50[^.] | Science (too specific, subcategories are partly handled)
#  ^64[^.] | Home & family management
#  ^79[^.] | Sports, games & entertainment
#  ^91[^.] | Geography & travel
#  ^92[^.] | Biography & genealogy

# ! order matters: first come first serve, rearranging might result in false
# positives

mappingDDC = [
        ["04 earth sciences",
            re.compile(
                '^55[^.]+.*'
                '|^56[^.]+.*'
                '|^ddc 55[^.]+.*'
                '|^ddc 56[^.]+.*'
                '|.*earth sciences and geology$'
                '|.*550\s*\|\s*geowissenschaften.*'
                '|^912$'
                '|geowissenschaften$'
            )
        ],
        ["11 medical and health sciences",
            re.compile(
                '^61[^.]+.*'
                '|^ddc 61[^.]+.*'
                '|^medizin und gesundheit'
                )
        ],
        ["06 biological sciences",
            re.compile(
                '^57[^.]+.*'
                '|^58[^.]+.*'
                '|^59[^.]+.*'
                '|^ddc 57[^.]+.*'
                '|^ddc 58[^.]+.*'
                '|^ddc 59[^.]+.*'
                '|.*naturwissenschaften::570.*'
                '|.*naturwissenschaften::580.*'
                '|.*naturwissenschaften::590.*'
                '|biology'
                )
        ],
        ["08 information and computing sciences",
            re.compile(
                '^00[^.]+.*'
                '|^01[^.]+.*'
                '|^02[^.]+.*'
                '|^ddc 00[^.]+.*'
                '|^ddc 01[^.]+.*'
                '|^ddc 02[^.]+.*'
                '|.*allgemeines, wissenschaft::000.*$'
                '|^bibliotheks- und informationswissenschaften$'
                )
        ],
        ["14 economics",
            re.compile(
                '^33[^.]+.*'
                '|^ddc 33[^.]+.*'
                '|^wirtschaft$'
                )
        ],
        ["09 engineering",
            re.compile(
                '^62[^.]+.*'
                '|^ddc 62[^.]+.*'
                '|.*technik::620.*'
                )
        ],
        ["02 physical science",
            re.compile(
                '^52[^.]+.*'
                '|^53[^.]+.*'
                '|^ddc 52[^.]+.*'
                '|^ddc 53[^.]+.*'
                '|.*530 \| physik.*'
                )
        ],
        ["21 history and archaeology",
                re.compile(
                    '^90[^.]+.*'
                    '|^93[^.]+.*'
                    '|^94[^.]+.*'
                    '|^95[^.]+.*'
                    '|^96[^.]+.*'
                    '|^97[^.]+.*'
                    '|^98[^.]+.*'
                    '|^99[^.]+.*'
                    '|^ddc 90[^.]+.*'
                    '|^ddc 93[^.]+.*'
                    '|^ddc 94[^.]+.*'
                    '|^ddc 95[^.]+.*'
                    '|^ddc 96[^.]+.*'
                    '|^ddc 97[^.]+.*'
                    '|^ddc 98[^.]+.*'
                    '|^ddc 99[^.]+.*'
                    '|^271.*'
                    )
        ],
        ["03 chemical science",
                re.compile(
                    '^54[^.]+.*'
                    '|^54[^.]+.*'
                    '|.*540 \| chemie.*'
                    )
        ],
        ["20 language, communication and culture",
                re.compile(
                    '^4\d+[^.]+.*'
                    '|^8\d+[^.-]+.*'
                    '|^306.*'
                    '|^ddc 4[^.]+.*'
                    '|^ddc 8[^.]+.*'
                    '|^ddc 306.*'
                    '|^8 language\. linguistics\. literature$'
                    '|^81 linguistics and languages'
                    '|.*dewey decimal classification::400 \| sprache, linguistik.*$'
                    '|.*dewey decimal classification::800 \| literatur, rhetorik, literaturwissenschaft.*$'
                    )
        ],
        ["16 studies in human society",
                re.compile(
                    '^30[^.]+.*'
                    '|^32[^.]+.*'
                    '|^36[^.]+.*'
                    '|^ddc 30[^.]+.*'
                    '|^ddc 32[^.]+.*'
                    '|^ddc 36[^.]+.*'
                    '|.*sozialwissenschaften, soziologie, anthropologie::330$'
                    '|.*sozialwissenschaften, soziologie, anthropologie::330.*'
                    '|.*sozialwissenschaften, soziologie, anthropologie::360.*'
                    '|^soziale probleme und sozialdienste; verbände$'
                    '|^0 social sciences'
                    '|^3 social sciences$'
                    '|^sozialwissenschaften$'
                    )
        ],
        ["07 agricultural and veterinary science",
                re.compile(
                    '^63[^.]+.*'
                    '|^ddc 63[^.]+.*'
                    '|^landwirtschaft und verwandte bereiche$'
                    '|.*technik::630.*'
                    )
        ],
        ["17 psychology and cognitive sciences",
                re.compile(
                    '^15[^.]+.*'
                    '|^ddc 15[^.]+.*'
                    '|^psychologie$'
                    )
        ],
        ["10 technology",
                re.compile(
                    '^60[^.]+.*'
                    '|^ddc 60[^.]+.*'
                    )
        ],
        ["13 education",
                re.compile(
                    '^37[^.]+.*'
                    '^507.*'
                    '|^ddc 37[^.]+.*'
                    '|^ddc 507.*'
                    '|.*sozialwissenschaften, soziologie, anthropologie::370.*'
                    )
        ],
        ["01 mathematical science",
                re.compile(
                    '^31\d+.*'
                    '|^51[^.]+.*'
                    '|^ddc 31[^.]+.*'
                    '|^ddc 51[^.]+.*'
                    '|.*510 \| mathematik.*'
                    )
        ],
        ["18 law and legal studies",
                re.compile(
                    '^34[^.]+.*'
                    '|^ddc 34[^.]+.*'
                    '|.*sozialwissenschaften, soziologie, anthropologie::340.*'
                    '|^recht$'
                    )
        ],
        ["22 philosophy and religious studies",
                re.compile(
                    '^(1|2)\d+.*'
                    '|^507.*'
                    '|^ddc (1|2)[^.]+.*'
                    '|^ddc 507.*'

                    )
        ],
        ["09 engineering",
                re.compile(
                    '^62[^.]+.*'
                    '|^66[^.]+.*'
                    '|^67[^.]+.*'
                    '|^68[^.]+.*'
                    '|^ddc 62[^.]+.*'
                    '|^ddc 66[^.]+.*'
                    '|^ddc 67[^.]+.*'
                    '|^ddc 68[^.]+.*'
                    )
        ],
        ["10 technology",
                re.compile(
                    '^60[^.]+.*'
                    '|^ddc 60[^.]+.*'
                    '|.*600 \| technik.*$')
        ],
        ["19 studies in creative arts and writing",
                re.compile(
                    '^07[^.]+.*'
                    '|^70[^.]+.*'
                    '|^73[^.]+.*'
                    '|^74[^.]+.*'
                    '|^75[^.]+.*'
                    '|^76[^.]+.*'
                    '|^77[^.]+.*'
                    '|^78[^.]+.*'
                    '|^ddc 07[^.]+.*'
                    '|^ddc 70[^.]+.*'
                    '|^ddc 73[^.]+.*'
                    '|^ddc 74[^.]+.*'
                    '|^ddc 75[^.]+.*'
                    '|^ddc 76[^.]+.*'
                    '|^ddc 77[^.]+.*'
                    '|^ddc 78[^.]+.*'
                    )
        ],
        ["15 commerce, management, tourism and services",
                re.compile(
                    '^38[^.]+.*'
                    '|^65[^.].*'
                    '|^ddc 38[^.]+.*'
                    '|^ddc 65[^.]+.*'
                    '|.*sozialwissenschaften, soziologie, anthropologie::380.*'
                    )
        ],
        ["12 built environment and design",
                re.compile(
                    '^69[^.*]'
                    '|^71[^.*]'
                    '|^72[^.*]'
                    '|^ddc 69[^.]+.*'
                    '|^ddc 71[^.]+.*'
                    '|^ddc 72[^.]+.*'
                    )
        ]
]
