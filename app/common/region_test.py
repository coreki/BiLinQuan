#coding=utf-8
#region.py

from region import RegionName

if __name__ == '__main__':

    for province in RegionName.kind_region[1]:
        province_id = province[0]
        province_name = province[1]
        print('%d %s' % (province_id,province_name))
        for city in RegionName.kind_region[province_id]:
            city_id = city[0]
            city_name = city[1]
            print('    %d %s' % (city_id, city_name))
            for district in RegionName.kind_region[city_id]:
                district_id = district[0]
                district_name = district[1]
                print('         %d %s' % (district_id, district_name))
