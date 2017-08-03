
import datetime
import numpy
import hashlib
from pygeoip import GeoIP, GeoIPError
from random import choice, randint
import os
import re
import socket
import sys
import threading
import random
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.db.models import Count
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import Context, loader, RequestContext
import requests
import json
import time
from django.utils import timezone
from django.utils.datastructures import MultiValueDictKeyError
from django.views.decorators.csrf import csrf_exempt

from stats.models import *
from django.db import models

from django.conf import settings
import dateutil.parser
import pycountry
import operator
import reverse_geocoder as rg
import math
from world_regions.models import Region
import copy
from ast import literal_eval
from itertools import tee, islice, chain, izip
from six import string_types
import time
from urllib import urlopen
import collections
import csv
import difflib

import geograpy
from django.http import JsonResponse
from collections import defaultdict
from itertools import groupby


if not settings.configured:
    settings.configure()


####### TEMPLATE RENDERERS #######
def show_sign_in_page(request):
    '''
    Shows login page.
    '''
    try:
        username = request.POST['username']
        password = request.POST['password']
    except:
        return render_to_response('authentication_page.html', {
        }, context_instance=RequestContext(request))

    # try logging in
    user = authenticate(username = username, password = password)

    # Invalid login
    if user is None:
        return render_to_response('authentication_page.html', {
            'error_message': "Invalid username or password. Please try again.",
        }, context_instance=RequestContext(request))
    # De-activated user
    elif not user.is_active:
        return render_to_response('authentication_page.html', {
            'error_message': "The account you are trying to use has been disabled.<br/>" + 
            "Please contact a system administrator.",
        }, context_instance=RequestContext(request))
    # Valid login, active user
    else:
        login(request, user)
        return HttpResponseRedirect('../')



def show_log(request):
    '''
    Renders the logs.
    '''
    total = 100
    percent = cookieCount = 0
    if request.COOKIES.has_key( 'visits' ):
        cookieCount = request.COOKIES.get('visits')
        cookieCount = int(cookieCount)
        percent = float(cookieCount)/total
        percent = percent * 100

    response = render_to_response('showlog.html', {'current_path': request.get_full_path(), 'percent': percent, 'cookieCount': cookieCount}, context_instance=RequestContext(request))
    if request.COOKIES.has_key( 'visits' ):
        cookieCount = request.COOKIES.get('visits')
        cookieCount = int(cookieCount)
        cookieCount += 1
        response.set_cookie('visits', cookieCount)
    else:
        response.set_cookie('visits', '1')
    # return render_to_response('showlog.html', {}, context_instance=RequestContext(request))
    # response = render_to_response('showlog.html', {}, context_instance=RequestContext(request))
    return response



def show_error_log(request):
    '''
    Renders the logs.
    '''
    return render_to_response('showerrorlog.html', {
    }, context_instance=RequestContext(request))



def show_error_details(request, error_id):
    '''
    Renders the template which shows detailed error info.
    '''
    error_obj = get_object_or_404(Error, pk=error_id)
    # countryLog = LogEvent.objects.filter(date__range = (date_from, timezone.now())).values('netInfo__country').annotate(count=Count('netInfo__country'))
    actions = LogEvent.objects.values('date', 'action__name').filter(date__lte=error_obj.date, user=error_obj.logEvent.user, machine=error_obj.logEvent.machine).order_by('-date')[:10]
    for action in actions:
        action['name'] = action['action__name']
        del(action['action__name'])

    return render_to_response('errordetails.html', {
        "id": error_id,
        "description": error_obj.description,
        "stack_trace": error_obj.stackTrace,
        "severity": error_obj.severity,
        "user_comments": error_obj.userComments,
        "execution_log": error_obj.executionLog,
        "date": error_obj.date,
        "source": error_obj.logEvent.source,
        "platform": error_obj.logEvent.machine.getPlatform(),
        "actions": actions,
    }, context_instance=RequestContext(request))



def show_debug(request):
    '''
    For debugging use only, will show a form where you can submit log events.
    '''
    if settings.DEBUG:
        return render_to_response('debug.html', {
        }, context_instance=RequestContext(request))
    else:
        raise Http404



def show_debug_error(request):
    '''
    For debugging use only, will show a form where you can submit errors to be logged.
    '''
    if settings.DEBUG:
        return render_to_response('debugerr.html', {
        }, context_instance=RequestContext(request))
    else:
        raise Http404



def help(request):
    '''
    Renders the help page.
    '''
    return render_to_response('help.html', {'current_path': request.get_full_path()}, context_instance=RequestContext(request))


# https://stackoverflow.com/questions/15377832/pycountries-convert-country-names-possibly-incomplete-to-countrycodes
def table(request):
    if request.user.is_authenticated():
        newCountries = []
        cosas = []
        with open('statsPage/static/countries.txt', 'r') as outfile:
            for line in outfile.readlines():
                cosas = [x.name.lower() for x in pycountry.countries]
                matching_countries = difflib.get_close_matches(line, cosas)
                u_m_c = [str(i) for i in matching_countries]
                confidence = difflib.SequenceMatcher(None, matching_countries, line).ratio()
                for each in u_m_c:
                    word = each.strip()
                    laLinea = line.strip()
                    if laLinea == word:
                       newCountries.append(laLinea) 

        newCountries = [element.title() for element in newCountries]
        alphaCodes = []
        for country in newCountries:
            c_name = pycountry.countries.get(name=country.encode("utf-8"))
            alphaCodes.append(c_name.alpha_2)

        regionsNew = []
        for aC in alphaCodes:
            region = Region.objects.get(countries__country=aC)
            regionsNew.append(region)
            
        regionsList = []
        for i in regionsNew:
            if i not in regionsList:
                regionsList.append(i)

        countriesList = []
        for i in newCountries:
            if i not in countriesList:
                countriesList.append(i)

        f = open('statsPage/static/csv/countryCount.csv', 'rb')
        reader = csv.reader(f)
        countryCount = []
        for row in reader:
            for country in countriesList:
                if country in row:
                    nested = []
                    nested.append(country)
                    nested.append(int(row[0]))
                    c_name = pycountry.countries.get(name=country.encode("utf-8"))
                    nested.append(c_name.alpha_2)
                    countryCount.append(nested)

        regionCount = []
        for region in regionsList:
            for country in countryCount:
                cReg = Region.objects.get(countries__country=country[2])
                if region == cReg:
                   nested = []
                   nested.append(cReg)
                   nested.append(country[1])
                   regionCount.append(nested)


        regionDict = {}
        for reg in regionCount:
            if regionDict.has_key(reg[0]):
                regionDict[reg[0]] += reg[1]
            else:
                regionDict[reg[0]] = reg[1]

        return render_to_response('global_stats/table.html', {'current_path': request.get_full_path(), 'regionDict': regionDict, 'countryCount': countryCount, 'countriesList': countriesList, 'regionsList': regionsList, 'regionsNew': regionsNew, 'newCountries': newCountries}, context_instance = RequestContext(request))
    else:
        return render_to_response('showlog.html', {}, context_instance = RequestContext(request))


def geo_stats(request):
    if request.user.is_authenticated():
        netinfo = NetInfo.objects.all()
        regions = WorldRegionsRegion.objects.all()
        countries = WorldRegionsRegioncountry.objects.all()
        country_names = []
        country_abbr = []
        all_it = []
        for each in countries:
            abbr = each.country
            if abbr.encode("utf-8") == 'AN':
                pass
            else:
                c_name = pycountry.countries.get(alpha_2=abbr.encode("utf-8"))
                country_names.append(c_name.name)
                country_abbr.append(abbr.encode("utf-8"))
                nested = []
                nested.append(abbr.encode("utf-8"))
                nested.append(c_name.name)
                all_it.append(nested)


        with_R = []
        for one in all_it:
            n_R = []
            region = Region.objects.get(countries__country=one[0])
            n_R.append(region.name)
            n_R.append(one[1])
            with_R.append(n_R)

        regions_bro = []
        el_paiz = []
        outer_dict = {}
        outer_child = []
        for each in with_R:
            if each[0] in regions_bro:
                for out in outer_child:
                    if each[0] == out['name']:
                        nested_d = {}
                        nested_d["name"] = each[1]
                        nested_d["size"] = 0
                        out['children'].append(nested_d)
            else:
                regions_bro.append(each[0])
                nested_dict = {}
                nested_dict["name"] = each[0]
                nested_dict["children"] = []
                country_dict = {}
                country_dict["name"] = each[1]
                country_dict["size"] = 0
                nested_dict["children"].append(country_dict)
                outer_child.append(nested_dict)

        outer_dict["name"] = "usage"
        outer_dict["children"] = outer_child

        with open('statsPage/static/json/geo_stats.json', 'w') as outfile:
            json.dump(outer_dict, outfile)

        newCountries = [] 
        cosas = [] 
        with open('statsPage/static/countries.txt', 'r') as outfile:
            for line in outfile.readlines():
                cosas = [x.name.lower() for x in pycountry.countries]
                matching_countries = difflib.get_close_matches(line, cosas)
                u_m_c = [str(i) for i in matching_countries]
                confidence = difflib.SequenceMatcher(None, matching_countries, line).ratio()
                for each in u_m_c:
                    word = each.strip()
                    laLinea = line.strip()
                    if laLinea == word:
                       newCountries.append(laLinea) 

        newCountries = [element.title() for element in newCountries]
        alphaCodes = [] 
        for country in newCountries:
            c_name = pycountry.countries.get(name=country.encode("utf-8"))
            alphaCodes.append(c_name.alpha_2)

        regionsNew = [] 
        for aC in alphaCodes:
            region = Region.objects.get(countries__country=aC)
            regionsNew.append(region)
     
        regionsList = [] 
        for i in regionsNew:
            if i not in regionsList:
                regionsList.append(i)

        countriesList = [] 
        for i in newCountries:
            if i not in countriesList:
                countriesList.append(i)

        f = open('statsPage/static/csv/countryCount.csv', 'rb')
        reader = csv.reader(f)
        countryCount = [] 
        for row in reader:
            for country in countriesList:
                if country in row: 
                    nested = [] 
                    nested.append(country)
                    nested.append(int(row[0]))
                    c_name = pycountry.countries.get(name=country.encode("utf-8"))
                    nested.append(c_name.alpha_2)
                    countryCount.append(nested)

        regionCount = [] 
        for region in regionsList:
            for country in countryCount:
                cReg = Region.objects.get(countries__country=country[2])
                if region == cReg:
                   nested = [] 
                   nested.append(cReg)
                   nested.append(country[1])
                   regionCount.append(nested)


        regionDict = {} 
        for reg in regionCount:
            if regionDict.has_key(reg[0]):
                regionDict[str(reg[0])] += reg[1]
            else:
                regionDict[str(reg[0])] = reg[1]

        thatNew = {}
        newNew = {}
        listo = []
        forCheck = {}
        forList = []
        for key, value in regionDict.iteritems():
            nested = {}
            nested["name"] = key
            nested["children"] = [] 
            listo.append(nested)
            forList.append(nested)

        newNew["name"] = "esgf"
        newNew["children"] = listo
        forCheck["name"] = "esgf"
        forCheck["children"] = listo


        check = {}
        yesTrue = 0
        for key, value in newNew.iteritems():
            for each in value:
                if type(each) is dict:
                    for country in countryCount:
                        for k, v in each.iteritems():
                            cReg = Region.objects.get(countries__country=country[2])
                            if type(v) is list:
                                if yesTrue == 1:
                                   nested = {}
                                   nested["name"] = country[0] + ": " + str(country[1])
                                   nested["size"] = country[1]
                                   v.append(nested)    
                                   yesTrue = 0
                            if v == str(cReg):
                               yesTrue = 1
        
        for key, value in newNew.iteritems():
            for k, v in regionDict.iteritems():
                if value == k:
                    print "values are equal"

        with open('statsPage/static/json/countGeoStats.json', 'w') as outfile:
            json.dump(newNew, outfile)

        return render_to_response('global_stats/geo_stats.html', {'current_path': request.get_full_path()}, context_instance = RequestContext(request))
    else:
        return render_to_response('showlog.html', {}, context_instance = RequestContext(request))


# https://stackoverflow.com/questions/5389507/iterating-over-every-two-elements-in-a-list
def pairwise(iterable):
    "s -> (s0, s1), (s2, s3), (s4, s5), ..."
    a = iter(iterable)
    return izip(a, a)


def world_stats(request):
    if request.user.is_authenticated():
        netinfo = NetInfo.objects.all()
        regions = WorldRegionsRegion.objects.all()
        countries = WorldRegionsRegioncountry.objects.all()
        country_names = []
        for each in countries:
            abbr = each.country
            if abbr.encode("utf-8") == 'AN':
                pass
            else:
                c_name = pycountry.countries.get(alpha_2=abbr.encode("utf-8"))
                country_names.append(c_name.name)

        newCountries = [] 
        cosas = [] 
        with open('statsPage/static/countries.txt', 'r') as outfile:
            for line in outfile.readlines():
                cosas = [x.name.lower() for x in pycountry.countries]
                matching_countries = difflib.get_close_matches(line, cosas)
                u_m_c = [str(i) for i in matching_countries]
                confidence = difflib.SequenceMatcher(None, matching_countries, line).ratio()
                for each in u_m_c:
                    word = each.strip()
                    laLinea = line.strip()
                    if laLinea == word:
                       newCountries.append(laLinea) 

        newCountries = [element.title() for element in newCountries]
        alphaCodes = [] 
        for country in newCountries:
            c_name = pycountry.countries.get(name=country.encode("utf-8"))
            alphaCodes.append(c_name.alpha_2)

        regionsNew = [] 
        for aC in alphaCodes:
            region = Region.objects.get(countries__country=aC)
            regionsNew.append(region)
     
        regionsList = [] 
        for i in regionsNew:
            if i not in regionsList:
                regionsList.append(i)

        countriesList = [] 
        for i in newCountries:
            if i not in countriesList:
                countriesList.append(i)

        f = open('statsPage/static/csv/countryCount.csv', 'rb')
        reader = csv.reader(f)
        countryCount = [] 
        for row in reader:
            for country in countriesList:
                if country in row: 
                    nested = [] 
                    nested.append(country)
                    nested.append(int(row[0]))
                    c_name = pycountry.countries.get(name=country.encode("utf-8"))
                    nested.append(c_name.alpha_2)
                    countryCount.append(nested)

        regionCount = [] 
        for region in regionsList:
            for country in countryCount:
                cReg = Region.objects.get(countries__country=country[2])
                if region == cReg:
                   nested = [] 
                   nested.append(cReg)
                   nested.append(country[1])
                   regionCount.append(nested)


        regionDict = {} 
        for reg in regionCount:
            if regionDict.has_key(reg[0]):
                regionDict[reg[0]] += reg[1]
            else:
                regionDict[reg[0]] = reg[1]

        with open('statsPage/static/csv/testing.csv', 'wb') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["Rank", "Country (or dependent territory)", "Population", "Date"])
            i = 1
            for paiz in countryCount:
                writer.writerow([i, paiz[0], paiz[1], time.strftime("%d/%m/%Y")])
                i+=1

        f = open('statsPage/static/csv/testing.csv', 'rb')
        reader = csv.reader(f)
        count = []
        for row in reader:
            if row[2] != 'Population':
                count.append(int(row[2]))

        print "     "
        average = numpy.mean(count)
        print average
        stdDev = numpy.std(count)
        print stdDev
        variance = numpy.var(count)
        print variance
        print "     "

        return render_to_response('global_stats/world_stats.html', {'current_path': request.get_full_path(), 'regionDict': regionDict, 'countryCount': countryCount, 'countriesList': countriesList, 'regionsList': regionsList, 'regionsNew': regionsNew, 'newCountries': newCountries, 'country_names': country_names, 'countries': countries, 'regions': regions, 'netinfo': netinfo}, context_instance = RequestContext(request))
    else:
        return render_to_response('showlog.html', {}, context_instance = RequestContext(request))


# gathers the next and previous in a list and returns
# current, next, and previous to the call
# used in a few places, do not delete
def previous_and_next(some_iterable):
    prevs, items, nexts = tee(some_iterable, 3)
    prevs = chain([None], prevs)
    nexts = chain(islice(nexts, 1, None), [None])
    return izip(prevs, items, nexts)



def nested_d3(request):
    error_c = 0
    if request.user.is_authenticated():
        newNew = []
        f = open('statsPage/static/csv/url.csv', 'rb')
        reader = csv.reader(f)
        countryCount = []
        var1 = []
        for row in reader:
            if type(row) == list:
                if row[0] != 'url':
                    # newNew.append(row)
                    if 'cmip3' not in row[0]:
                        if 'input4MIPs' not in row[0]:
                            newNew.append(row)
                            nested = {}
                            nested['key'] = row
                            var1.append(nested)

        urls = []
        for new in newNew:
            for each in new:
                each = each.split(os.sep)
                urls.append(each)
                
        lengthO = len(urls[0])

        for each in urls:
            if len(each) == 18:
               del each[:5]

        institutions = []
        save = []
        dontClick = []
        for each in urls:
            nested = {}
            # nested['institution'] = each[3]
            # nested['model'] = each[4]
            # nested['experiment'] = each[5]
            # nested['timeFreq'] = each[6]
            # nested['variable'] = each[7]
            # nested['possVar'] = each[8]
            # dontClick.append(each[7])
            # save.append(nested)

            if type(each[11]) == int: 
                nested['institution'] = each[3]
                nested['model'] = each[4]
                nested['variable'] = each[10]
                nested['experiment'] = each[5]
                nested['timeFreq'] = each[6]
                nested['possVar'] = each[11]
                dontClick.append(each[10])
                save.append(nested)
            elif (each[11][0] == 'v') and (each[11][1].isdigit()):
                nested['institution'] = each[3]
                nested['model'] = each[4]
                nested['variable'] = each[10]
                nested['experiment'] = each[5]
                nested['timeFreq'] = each[6]
                nested['possVar'] = each[11]
                dontClick.append(each[10])
                save.append(nested)
            elif (each[10][0] == 'v') and (each[10][1].isdigit()):
                nested['institution'] = each[3]
                nested['model'] = each[4]
                nested['variable'] = each[11]
                nested['experiment'] = each[5]
                nested['timeFreq'] = each[6]
                nested['possVar'] = each[10]
                dontClick.append(each[11])
                save.append(nested)
            elif type(each[10]) == int: 
                nested['institution'] = each[3]
                nested['model'] = each[4]
                nested['variable'] = each[11]
                nested['experiment'] = each[5]
                nested['timeFreq'] = each[6]
                nested['possVar'] = each[10]
                dontClick.append(each[11])
                save.append(nested)
            else:
                nested['institution'] = each[3]
                nested['model'] = each[4]
                nested['variable'] = each[10]
                nested['experiment'] = each[5]
                nested['timeFreq'] = each[6]
                nested['possVar'] = each[11]
                dontClick.append(each[10])
                save.append(nested)
 
        models = []
        for each in urls:
            models.append(each[4])

        noSkate = []
        for inst in institutions:
            nested = {}
            nested['key'] = inst
            noSkate.append(nested)

        noSkate = unique_and_count(noSkate)
        save = unique_and_count(save)

        copied_list = save[:]
        for each in copied_list:
            if each['count'] < 250:
                save.remove(each)


        for no in noSkate:
            no['value'] = no.pop('count')

        for no in save:
            no['value'] = no.pop('count')

        with open('statsPage/static/json/noSkate.json', 'w') as f:
            # json.dump(noSkate, f)
            json.dump(save, f)

        noSkate = json.dumps(noSkate)
        save = json.dumps(save)

        return render_to_response('action_stats/nested_d3.html', { 'current_path': request.get_full_path(), 'dontClick': dontClick, 'save': save, 'noSkate': noSkate, 'institutions': institutions, 'urls': urls, 'newNew': newNew }, context_instance=RequestContext(request))
    else:
        return render_to_response('showlog.html', {}, context_instance = RequestContext(request))

def nested_experiment(request):
    error_c = 0
    if request.user.is_authenticated():
        newNew = []
        f = open('statsPage/static/csv/url.csv', 'rb')
        reader = csv.reader(f)
        countryCount = []
        var1 = []
        for row in reader:
            if type(row) == list:
                if row[0] != 'url':
                    # newNew.append(row)
                    if 'cmip3' not in row[0]:
                        if 'input4MIPs' not in row[0]:
                            newNew.append(row)
                            nested = {}
                            nested['key'] = row
                            var1.append(nested)

        urls = []
        for new in newNew:
            for each in new:
                each = each.split(os.sep)
                urls.append(each)
                
        lengthO = len(urls[0])

        for each in urls:
            if len(each) == 18:
               del each[:5]

        institutions = []
        save = []
        dontClick = []
        for each in urls:
            nested = {}
            # nested['experiment'] = each[5]
            # nested['timeFreq'] = each[6]
            # nested['variable'] = each[7]
            # nested['possVar'] = each[8]
            # dontClick.append(each[7])
            # save.append(nested)

            if type(each[11]) == int: 
                nested['variable'] = each[10]
                nested['experiment'] = each[5]
                nested['timeFreq'] = each[6]
                nested['possVar'] = each[11]
                dontClick.append(each[10])
                save.append(nested)
            elif (each[11][0] == 'v') and (each[11][1].isdigit()):
                nested['variable'] = each[10]
                nested['experiment'] = each[5]
                nested['timeFreq'] = each[6]
                nested['possVar'] = each[11]
                dontClick.append(each[10])
                save.append(nested)
            elif (each[10][0] == 'v') and (each[10][1].isdigit()):
                nested['variable'] = each[11]
                nested['experiment'] = each[5]
                nested['timeFreq'] = each[6]
                nested['possVar'] = each[10]
                dontClick.append(each[11])
                save.append(nested)
            elif type(each[10]) == int: 
                nested['variable'] = each[11]
                nested['experiment'] = each[5]
                nested['timeFreq'] = each[6]
                nested['possVar'] = each[10]
                dontClick.append(each[11])
                save.append(nested)
            else:
                nested['variable'] = each[10]
                nested['experiment'] = each[5]
                nested['timeFreq'] = each[6]
                nested['possVar'] = each[11]
                dontClick.append(each[10])
                save.append(nested)



        models = []
        for each in urls:
            models.append(each[4])

        noSkate = []
        for inst in institutions:
            nested = {}
            nested['key'] = inst
            noSkate.append(nested)

        noSkate = unique_and_count(noSkate)
        save = unique_and_count(save)

        copied_list = save[:]
        for each in copied_list:
            if each['count'] < 250:
                save.remove(each)


        for no in noSkate:
            no['value'] = no.pop('count')

        for no in save:
            no['value'] = no.pop('count')

        with open('statsPage/static/json/noSkate.json', 'w') as f:
            json.dump(save, f)

        noSkate = json.dumps(noSkate)
        save = json.dumps(save)

        return render_to_response('action_stats/nested_experiment.html', { 'current_path': request.get_full_path(), 'dontClick': dontClick, 'save': save, 'noSkate': noSkate, 'institutions': institutions, 'urls': urls, 'newNew': newNew }, context_instance=RequestContext(request))
    else:
        return render_to_response('showlog.html', {}, context_instance = RequestContext(request))

def nested_var(request):
    error_c = 0
    if request.user.is_authenticated():
        var1 = []
        newNew = []
        f = open('statsPage/static/csv/url.csv', 'rb')
        reader = csv.reader(f)
        countryCount = []
        for row in reader:
            if type(row) == list:
                if row[0] != 'url':
                    if 'cmip3' not in row[0]:
                        if 'input4MIPs' not in row[0]:
                            newNew.append(row)
                            nested = {}
                            nested['key'] = row
                            var1.append(nested)

        urls = []
        for new in newNew:
            for each in new:
                each = each.split(os.sep)
                urls.append(each)
                
        lengthO = len(urls[0])

        for each in urls:
            if len(each) == 18:
               del each[:5]

        string = 'v1'
        institutions = []
        save = []
        dontClick = []
        if (string[0] == 'v') and (string[1].isdigit()):
            print "YES THAT WORKS"


        count = 0
        printToLog = []
        addToLog = []
        for each in urls:
            if count < 5:
               printToLog.append(each) 
               count += 1
            nested = {}
            forLog = {}
            if type(each[11]) == int:
                forLog['each[11]==int'] = each
                addToLog.append(each)
                nested['variable'] = each[10]
                nested['experiment'] = each[5]
                nested['timeFreq'] = each[6]
                nested['possVar'] = each[11]
                dontClick.append(each[6])
                save.append(nested)
            elif (each[11][0] == 'v') and (each[11][1].isdigit()):
                forLog['each[11]==vint'] = each
                addToLog.append(each)
                nested['variable'] = each[10]
                nested['experiment'] = each[5]
                nested['timeFreq'] = each[6]
                nested['possVar'] = each[11]
                dontClick.append(each[6])
                save.append(nested)
            elif (each[10][0] == 'v') and (each[10][1].isdigit()):
                forLog['each[10]==vint'] = each
                addToLog.append(each)
                nested['variable'] = each[11]
                nested['experiment'] = each[5]
                nested['timeFreq'] = each[6]
                nested['possVar'] = each[10]
                dontClick.append(each[6])
                save.append(nested)
            elif type(each[10]) == int:
                forLog['each[10]==int'] = each
                addToLog.append(each)
                nested['variable'] = each[11]
                nested['experiment'] = each[5]
                nested['timeFreq'] = each[6]
                nested['possVar'] = each[10]
                dontClick.append(each[6])
                save.append(nested)
            else:
                nested['variable'] = each[10]
                nested['experiment'] = each[5]
                nested['timeFreq'] = each[6]
                nested['possVar'] = each[11]
                dontClick.append(each[6])
                save.append(nested)
                forLog['else'] = each
                addToLog.append(each)

            # nested['variable'] = each[10]
            # nested['experiment'] = each[5]
            # nested['timeFreq'] = each[6]
            # nested['possVar'] = each[11]
            # dontClick.append(each[6])
            # save.append(nested)

        models = []
        for each in urls:
            models.append(each[4])


        noSkate = []
        for inst in institutions:
            nested = {}
            nested['key'] = inst
            noSkate.append(nested)

        noSkate = unique_and_count(noSkate)
        save = unique_and_count(save)
        
        copied_list = save[:]
        for each in copied_list:
            if each['count'] < 250:
                save.remove(each)

        for no in noSkate:
            no['value'] = no.pop('count')

        for no in save:
            no['value'] = no.pop('count')

        with open('statsPage/static/json/noSkate.json', 'w') as f:
            json.dump(save, f)

        with open('statsPage/static/json/var1.json', 'w') as f:
            json.dump(var1, f)

        with open('addToLog.json', 'w') as f:
            json.dump(addToLog, f)

        with open('printToLog.json', 'w') as f:
            json.dump(printToLog, f)

        noSkate = json.dumps(noSkate)
        save = json.dumps(save)

        return render_to_response('action_stats/nested_var.html', {'current_path': request.get_full_path(), 'dontClick': dontClick, 'save': save, 'noSkate': noSkate, 'institutions': institutions, 'urls': urls, 'newNew': newNew}, context_instance=RequestContext(request))
    else:
        return render_to_response('showlog.html', {}, context_instance = RequestContext(request))

def nested_timeFreq(request):
    error_c = 0
    if request.user.is_authenticated():

        newNew = []
        f = open('statsPage/static/csv/url.csv', 'rb')
        reader = csv.reader(f)
        countryCount = []
        var1 = []
        for row in reader:
            if type(row) == list:
                if row[0] != 'url':
                    if 'cmip3' not in row[0]:
                        if 'input4MIPs' not in row[0]:
                            newNew.append(row)
                            nested = {}
                            nested['key'] = row
                            var1.append(nested)

        urls = []
        for new in newNew:
            for each in new:
                each = each.split(os.sep)
                urls.append(each)
                
        lengthO = len(urls[0])

        for each in urls:
            if len(each) == 18:
               del each[:5]

        institutions = []
        save = []
        dontClick = []
        testing = []
        for each in urls:
            forTest = {}
            nested = {}
            # forTest['timeFreq'] = each[6]
            # nested['timeFreq'] = each[6]
            # nested['experiment'] = each[5]
            # nested['variable'] = each[7]
            # nested['possVar'] = each[8]
            # dontClick.append(each[7])
            # save.append(nested)
            # testing.append(forTest)

            if type(each[11]) == int:
                nested['variable'] = each[10]
                nested['experiment'] = each[5]
                nested['timeFreq'] = each[6]
                nested['possVar'] = each[11]
                dontClick.append(each[10])
                save.append(nested)
            elif (each[11][0] == 'v') and (each[11][1].isdigit()):
                nested['variable'] = each[10]
                nested['experiment'] = each[5]
                nested['timeFreq'] = each[6]
                nested['possVar'] = each[11]
                dontClick.append(each[10])
                save.append(nested)
            elif (each[10][0] == 'v') and (each[10][1].isdigit()):
                nested['variable'] = each[11]
                nested['experiment'] = each[5]
                nested['timeFreq'] = each[6]
                nested['possVar'] = each[10]
                dontClick.append(each[11])
                save.append(nested)
            elif type(each[10]) == int:
                nested['variable'] = each[11]
                nested['experiment'] = each[5]
                nested['timeFreq'] = each[6]
                nested['possVar'] = each[10]
                dontClick.append(each[11])
                save.append(nested)
            else:
                nested['variable'] = each[10]
                nested['experiment'] = each[5]
                nested['timeFreq'] = each[6]
                nested['possVar'] = each[11]
                dontClick.append(each[10])
                save.append(nested)


        models = []
        for each in urls:
            models.append(each[4])

        noSkate = []
        for inst in institutions:
            nested = {}
            nested['key'] = inst
            noSkate.append(nested)

        noSkate = unique_and_count(noSkate)
        save = unique_and_count(save)

        copied_list = save[:]
        for each in copied_list:
            if each['count'] < 250:
                save.remove(each)

        for no in noSkate:
            no['value'] = no.pop('count')

        for no in save:
            no['value'] = no.pop('count')

        with open('statsPage/static/json/testingFreq.json', 'w') as f:
            json.dump(testing, f)

        with open('statsPage/static/json/nestedTimeFreq.json', 'w') as f:
            json.dump(save, f)

        noSkate = json.dumps(noSkate)
        save = json.dumps(save)

        return render_to_response('action_stats/nested_timeFreq.html', { 'current_path': request.get_full_path(), 'dontClick': dontClick, 'save': save, 'noSkate': noSkate, 'institutions': institutions, 'urls': urls, 'newNew': newNew }, context_instance=RequestContext(request))
    else:
        return render_to_response('showlog.html', {}, context_instance = RequestContext(request))

def organizations(request):
    if request.user.is_authenticated():
        newNew = []
        f = open('statsPage/static/csv/organization.csv', 'rb')
        reader = csv.reader(f)
        countryCount = []
        for row in reader:
            newNew.append(row)

        laNew = []
        count = 0
        for each in newNew:
            count += 1
            nested = {}
            nested['label'] = each[0]
            laNew.append(nested)

        listCount = []
        copy_laNew = copy.copy(laNew)
        laNew = unique_and_count(laNew)
        listCount = unique_and_count(copy_laNew)
        newNew = []
        c = 758
        totalOrg = []
        for each in listCount:
            if int(each['count']) > int(c):
                ne = {}
                ne['label'] = each['label']
                ne['count'] = each['count']
                totalOrg.append(ne)
                newNew.append(each)

        orgCount = []
        for each in laNew:
            for tot in totalOrg:
                if tot['label'] == each['label']:
                    n = {}
                    n['label'] = tot['label']
                    n['count'] = tot['count']
                    orgCount.append(n)

        with open('statsPage/static/json/organizationJson.json', 'w') as f:
            json.dump(orgCount, f)

        laNew = json.dumps(laNew)
        newNew = json.dumps(newNew)
        totalOrg = json.dumps(totalOrg)
        orgCount = json.dumps(orgCount)

        return render_to_response('organizations.html', { 'current_path': request.get_full_path(), 'orgCount': orgCount, 'totalOrg': totalOrg, 'newNew': newNew, 'laNew': laNew }, context_instance=RequestContext(request))
    else:
        return render_to_response('showlog.html', {}, context_instance = RequestContext(request))

def testing(request):
    return render_to_response('testing.html', {}, context_instance = RequestContext(request))

def canonicalize_dict(x):
    "Return a (key, value) list sorted by the hash of the key"
    return sorted(x.items(), key=lambda x: hash(x[0]))

def unique_and_count(lst):
    "Return a list of unique dicts with a 'count' key added"
    grouper = groupby(sorted(map(canonicalize_dict, lst)))
    return [dict(k + [("count", len(list(g)))]) for k, g in grouper]


