#!/usr/bin/env python3
"""Offline DOS/8086 error matrix, actual mTCP + production main/UI readbacks.
ROBUST.EXE replaces BIOS keyboard input only; AI4DOS.EXE checks startup failures.
No provider requests. Packet-driver rejection TSRs are deliberate API mocks.
"""
import hashlib, json, os, shutil, struct, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; B=ROOT/'client/build'
BASE='SERVER=10.0.2.2\nPORT=9\nDEVICE=test-device\nSECRET=local-test-key\nCODEPAGE=437\n'
IP='PACKETINT 0x60\nHOSTNAME AI4DOS-QA\nIPADDR 10.0.2.15\nNETMASK 255.255.255.0\nGATEWAY 10.0.2.2\nMTU 1500\n'
CONF='[cpu]\ncputype=8086\ncycles=max\n[dosbox]\nmachine=hercules\nmemsize=1\n[ne2000]\nne2000=true\nnicbase=300\nnicirq=3\nmacaddr=AC:DE:48:10:40:02\nbackend=slirp\n[ethernet, slirp]\nrestricted=false\ndisable_host_loopback=false\n'
RESULT_FILE=B/'ROBUST-RESULTS.json'
results=[]
def run(name,cfg=BASE,ip=IP,driver=False,expect='Network unavailable.',machine='hercules',exe='ROBUST.EXE',arg='QA.CFG',env=True,mode='offline',precommands=()):
    if driver is True:
        src=Path(os.environ.get('NE2K_DRIVER',str(B/'NE2K.COM')))
        assert hashlib.sha256(src.read_bytes()).hexdigest()=='f95b36199a47bf7e6eb03cb9474e97d50cb9c23de08996a036bb525599e0b9f2'
        if src.resolve()!=(B/'NE2K.COM').resolve():shutil.copyfile(src,B/'NE2K.COM')
    if exe=='AI4DOS.EXE':machine='vgaonly' # DOSBox-X's initial Hercules console readback is unreliable.
    if expect=='Gateway unreachable.':mode='once'
    (B/'QA.CFG').unlink(missing_ok=True)
    if cfg is not None:(B/'QA.CFG').write_bytes(cfg.replace('\n','\r\n').encode('ascii'))
    (B/'QAMTCP.CFG').write_text(ip);(B/'QA.CONF').write_text(CONF.replace('machine=hercules','machine='+machine))
    for f in ['QA.LOG','QA.TXT','QA.OUT','QA.STA']:(B/f).unlink(missing_ok=True)
    lines=['@echo off','cd build','set QA_MODE='+mode]
    if driver:lines += [str(driver) if isinstance(driver,str) else 'NE2K.COM 0x60 3 0x300 > QAPKT.LOG']
    lines += ['set MTCPCFG='+('C:\\build\\QAMTCP.CFG' if env else '')]
    lines += list(precommands)
    lines += [f'{exe} {arg} > QA.OUT','if errorlevel 1 goto failed','echo PASS > QA.STA','goto finished',':failed','echo FAIL > QA.STA',':finished','DUMP.EXE']
    (B/'QA.BAT').write_bytes(('\r\n'.join(lines)+'\r\n').encode('ascii'))
    args=[os.environ.get('DOSBOX_X','dosbox-x'),'-defaultconf','-conf',str(B/'QA.CONF'),'-nogui','-silent','-fastlaunch','-time-limit','80']
    for cmd in [f'mount c "{ROOT / "client"}"','c:','build\\QA.BAT','exit']:args += ['-c',cmd]
    with (B/'QAEMU.LOG').open('wb') as log:subprocess.run(args,stdout=log,stderr=log,timeout=90,check=True)
    out=(B/'QA.OUT').read_text('cp437'); transcript=(B/'QA.TXT').read_text('cp437') if (B/'QA.TXT').exists() else ''
    log=(B/'QA.LOG').read_text() if (B/'QA.LOG').exists() else ''; state=(B/'QA.STA').read_text().strip()
    if exe=='ROBUST.EXE':
        assert log.startswith('PASS'),(name,log,out)
        assert expect in transcript,(name,expect,transcript)
        assert '%X' not in transcript and 'Init:' not in out and 'mTCP:' not in out,(name,out,transcript)
        if expect=='Network unavailable.':assert 'Gateway unreachable.' not in transcript,(name,transcript)
    else:
        assert state=='FAIL',(name,state)
        raw=(B/'QASCR.BIN').read_bytes();screen=raw[::2].decode('cp437')
        assert 'ERROR:' in screen and ('not found.' in screen or 'is invalid.' in screen),(name,screen)
        log='pre-UI console error verified from video memory'

    raw=(B/'QASCR.BIN').read_bytes()
    console='\n'.join(raw[::2].decode('cp437')[i:i+80].rstrip() for i in range(0,2000,80)).strip()
    result={'console':console,'case':name,'machine':machine,'state':state,'video':log.strip(),'stdout':out.strip(),'transcript':transcript.strip()}
    results.append(result);print(name,state,log.strip(),flush=True)
    RESULT_FILE.write_text(json.dumps(results,indent=2))

def rejection_tsr(name,code):
    # vector 60h, PKT DRVR at handler+3, access_type fails with carry and DH.
    handler=b'\xe9\x08\x00PKT DRVR'+b'\x55\x89\xe5\x83\x4e\x06\x01\xb6'+bytes([code])+b'\x5d\xcf'
    install=b'\xba\x03\x01\xb8\x60\x25\xcd\x21\xba\x20\x00\xb8\x00\x31\xcd\x21'
    (B/name).write_bytes(b'\xe9'+struct.pack('<H',len(handler))+handler+install)

if __name__=='__main__':
    rejection_tsr('FAILPKT.COM',11);rejection_tsr('BUSYPKT.COM',9)
    for machine in ['hercules','cga','ega','vgaonly']:
        run('missing driver / '+machine,machine=machine)
        for f in ['INFO.LOG']:(B/f).unlink(missing_ok=True)
        args=[os.environ.get('DOSBOX_X','dosbox-x'),'-defaultconf','-nogui','-silent','-fastlaunch','-machine',machine,'-set','cpu cputype=8086','-set','cpu cycles=max','-time-limit','35']
        for cmd in [f'mount c "{ROOT / "client"}"','c:','build\\INFO.EXE > build\\INFO.LOG','exit']:args+=['-c',cmd]
        with (B/'INFOEMU.LOG').open('wb') as log:subprocess.run(args,stdout=log,stderr=log,timeout=45,check=True)
        text=(B/'INFO.LOG').read_text();assert 'AI4DOS F1 PASS' in text,text
        results.append({'case':'F1 '+machine,'result':text.strip()});print('F1',machine,'PASS',flush=True)
    run('wrong interrupt',driver=True,ip=IP.replace('0x60','0x61'))
    run('driver signature present / access_type rejects',driver='FAILPKT.COM')
    run('driver API TYPE_INUSE rejection',driver='BUSYPKT.COM')
    run('MTCPCFG unset',env=False)
    run('MTCPCFG empty',ip='')
    run('missing IP (no DHCP lease)',driver=True,ip=IP.replace('IPADDR 10.0.2.15\n',''))
    run('zero IP (no address obtained)',driver=True,ip=IP.replace('10.0.2.15','0.0.0.0'),expect='No valid IP address assigned.')
    run('invalid mTCP IP',driver=True,ip=IP.replace('10.0.2.15','invalid'))
    run('missing gateway',driver=True,cfg=BASE.replace('10.0.2.2','10.0.3.2'),ip=IP.replace('GATEWAY 10.0.2.2\n',''),expect='Network gateway not configured.')
    run('expired DHCP lease',driver=True,ip=IP+'TIMESTAMP ( 1 )\nLEASE_TIME 1\n')
    run('out of range PACKETINT',ip=IP.replace('0x60','0x80'))
    run('invalid PACKETINT',ip=IP.replace('0x60','invalid'))
    run('closed port / valid static IP without DHCP',driver=True,expect='Gateway unreachable.')
    run('unreachable local subnet host',driver=True,cfg=BASE.replace('10.0.2.2','10.0.2.99'),expect='Gateway unreachable.')
    run('invalid gateway SERVER address',driver=True,cfg=BASE.replace('10.0.2.2','999.1.1.1'),expect='Invalid server address.')
    run('mTCP warning preserved',ip=IP.replace('HOSTNAME AI4DOS-QA','HOSTNAME AI4DOS-QA '))
    for name,cfg in [('missing CFG',None),('empty CFG',''),('typo key',BASE.replace('SERVER=','SERVRE=')),('missing device',BASE.replace('DEVICE=test-device\n','')),('missing port',BASE.replace('PORT=9\n','')),('missing secret',BASE.replace('SECRET=local-test-key\n','')),('long DEVICE',BASE.replace('test-device','x'*200)),('long SECRET',BASE.replace('local-test-key','x'*300)),('port nonnumeric',BASE.replace('PORT=9','PORT=x')),('port zero',BASE.replace('PORT=9','PORT=0')),('port overflow',BASE.replace('PORT=9','PORT=65536')),('unknown option',BASE+'UNKNOWN=x\n'),('PACKETINT in AI4DOS CFG',BASE+'PACKETINT=0x60\n'),('long SERVER',BASE.replace('10.0.2.2','x'*300)),('malformed line',BASE+'BROKEN\n'),('invalid codepage',BASE.replace('CODEPAGE=437','CODEPAGE=999'))]:
        run(name,cfg=cfg,exe='AI4DOS.EXE')
    run('alternative config filename',arg='C:\\build\\QA.CFG')
    for f in ['QA.CFG']:(B/f).unlink(missing_ok=True)
    RESULT_FILE.write_text(json.dumps(results,indent=2))

    print("DOS robustness matrix PASS: "+str(len(results))+" cases; pre-UI FAIL exit codes are expected rejections.")
