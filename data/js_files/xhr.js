/*
 * xhr.js - XMLHttpRequest helper class
 * (c) 2008-2010 Jo-Philipp Wich
 */
var ajaxcgi = "../cgi-bin/ajax";
var jsonheadstr = "Content-type: application/json";
XHR = function()
{
	this.reinit = function()
	{
		if (window.XMLHttpRequest) {
			this._xmlHttp = new XMLHttpRequest();
		}
		else if (window.ActiveXObject) {
			this._xmlHttp = new ActiveXObject("Microsoft.XMLHTTP");
		}
		else {
			alert("xhr.js: XMLHttpRequest is not supported by this browser!");
		}
	}

	this.busy = function() {
		if (!this._xmlHttp)
			return false;

		switch (this._xmlHttp.readyState)
		{
			case 1:
			case 2:
			case 3:
				return true;

			default:
				return false;
		}
	}

	this.abort = function() {
		if (this.busy())
			this._xmlHttp.abort();
	}

	this.get = function(ajaxmethod,data,callback)
	{
		this.reinit();

		var xhr  = this._xmlHttp;
		var code = this._encode_new(ajaxmethod, data);
		
		url = ajaxcgi;

		if (code)
			if (url.substr(url.length-1,1) == '&')
				url += code;
			else
				url += '?' + code;
			
		//url += '&token=' + navigator.userAgent;


		xhr.open('GET', url, false);

		/*xhr.onreadystatechange = function()
		{
			if (xhr.readyState == 4)
			{
				var json = parseData(xhr);
				if ( callback != null )
				{
					callback(json);
				}
			}
		}*/
		xhr.send(null);
		
		if (xhr.readyState == 4 && xhr.status == 200)
		{
			var json = parseData(xhr, "GET");
			if ( callback != null )
			{
				callback(json);
			}
		}
			
	}

	this.post = function(ajaxmethod,data,callback)
	{
		this.reinit();
		var that =this;
		(new XHR()).get("get_refresh_sessionid", null,  function(getdata){
			if ( getdata.sessionid != undefined )
				{
				   data.sessionid =  getdata.sessionid;
		       	   that.post2(ajaxmethod,data,callback);
				};
		});
	}

	this.post2 = function(ajaxmethod,data,callback)
	{
		var xhr  = this._xmlHttp;
		//var code = fhencrypt(this._encode_new(ajaxmethod, data));
		var code = this._encode_new(ajaxmethod, data);
		url = ajaxcgi;

		xhr.onreadystatechange = function()
		{
			if (xhr.readyState == 4)
			{
				var json = parseData(xhr, "POST");
				if ( callback != null )
				{
					callback(json);
				}
			}
		}

		xhr.open('POST', url, true);
		xhr.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
		//xhr.setRequestHeader('Content-length', code.length);
		//xhr.setRequestHeader('Connection', 'close');
		//alert(code);
		xhr.send(code);
	}

	this.cancel = function()
	{
		this._xmlHttp.onreadystatechange = function(){};
		this._xmlHttp.abort();
	}

	this.send_form = function(form,callback,extra_values)
	{
		var code = '';

		for (var i = 0; i < form.elements.length; i++)
		{
			var e = form.elements[i];

			if (e.options)
			{
				code += (code ? '&' : '') +
					form.elements[i].name + '=' + encodeURIComponent(
						e.options[e.selectedIndex].value
					);
			}
			else if (e.length)
			{
				for (var j = 0; j < e.length; j++)
					if (e[j].name) {
						code += (code ? '&' : '') +
							e[j].name + '=' + encodeURIComponent(e[j].value);
					}
			}
			else
			{
				code += (code ? '&' : '') +
					e.name + '=' + encodeURIComponent(e.value);
			}
		}

		if (typeof extra_values == 'object')
			for (var key in extra_values)
				code += (code ? '&' : '') +
					key + '=' + encodeURIComponent(extra_values[key]);

		return(
			(form.method == 'get')
				? this.get(form.getAttribute('action'), code, callback)
				: this.post(form.getAttribute('action'), code, callback)
		);
	}

	this._encode = function(obj)
	{
		obj = obj ? obj : { };
		obj['_'] = Math.random();

		if (typeof obj == 'object')
		{
			var code = '';
			var self = this;

			for (var k in obj)
				code += (code ? '&' : '') +
					k + '=' + encodeURIComponent(obj[k]);

			return code;
		}

		return obj;
	}
	
	this._encode_new = function(ajaxmethod, obj)
	{
		if(typeof obj == 'object')
		{
			obj = obj ? obj : { };
			obj['ajaxmethod'] = ajaxmethod;
			obj['_'] = Math.random();
		}else if(typeof obj == 'string'){
			obj += "&ajaxmethod=" + ajaxmethod;
			obj += "&_=" + Math.random();
		}
		

		if (typeof obj == 'object')
		{
			var code = '';
			var self = this;

			for (var k in obj)
				code += (code ? '&' : '') +
					k + '=' + encodeURIComponent(obj[k]);

			return code;
		}

		return obj;
	}
}

XHR.get = function(url, data, callback)
{
	(new XHR()).get(url, data, callback);
}

XHR.post = function(url, data, callback)
{
	(new XHR()).post(url, data, callback);
}


XHR.poll = function(interval, url, data, callback)
{
	if (isNaN(interval) || interval < 1)
		interval = 5;

	if (!XHR._q)
	{
		XHR._t = 0;
		XHR._q = [ ];
		XHR._r = function() {
			for (var i = 0, e = XHR._q[0]; i < XHR._q.length; e = XHR._q[++i])
			{
				if (!(XHR._t % e.interval) && !e.xhr.busy())
					e.xhr.get(e.url, e.data, e.callback);
			}

			XHR._t++;
		};
	}

	XHR._q.push({
		interval: interval,
		callback: callback,
		url:      url,
		data:     data,
		xhr:      new XHR()
	});

	XHR.run();
}

XHR.halt = function()
{
	if (XHR._i)
	{
		/* show & set poll indicator */
		try {
			document.getElementById('xhr_poll_status').style.display = '';
			document.getElementById('xhr_poll_status_on').style.display = 'none';
			document.getElementById('xhr_poll_status_off').style.display = '';
		} catch(e) { }

		window.clearInterval(XHR._i);
		XHR._i = null;
	}
}

XHR.run = function()
{
	if (XHR._r && !XHR._i)
	{
		/* show & set poll indicator */
		try {
			document.getElementById('xhr_poll_status').style.display = '';
			document.getElementById('xhr_poll_status_on').style.display = '';
			document.getElementById('xhr_poll_status_off').style.display = 'none';
		} catch(e) { }

		/* kick first round manually to prevent one second lag when setting up
		 * the poll interval */
		XHR._r();
		XHR._i = window.setInterval(XHR._r, 1000);
	}
}

XHR.running = function()
{
	return !!(XHR._r && XHR._i);
}

function parseData(xhr, method)
{
	var json = null;
	var ResponseHeader = xhr.getResponseHeader("Content-type");
	if (ResponseHeader == "application/json" || ResponseHeader == "text/plain; charset=utf-8" || ResponseHeader == "text/plain")
	{
		try
		{
		
			json = eval('(' + xhr.responseText + ')');
		}
		catch(e)
		{
			json = null;
		}
	}
	else
	{
		var indexplace = xhr.responseText.indexOf(jsonheadstr);
		if ( indexplace >= 0 )
		{
			var tempstr = xhr.responseText.substring(indexplace + jsonheadstr.length, xhr.responseText.length);
			try
			{
				json = eval('(' + tempstr + ')');
			}
			catch(e)
			{
				json = null;
			}
		}
	}
	if ( json != null && json.session_valid != null && json.session_valid != undefined )
	{
		if ( json.session_valid == 0 ) //session invalid, jump to login page
		{
			console.log("session is valid!")

			/*session无效时，不弹窗提示，直接退出到登录页面 */
            // if(parent.gSessionFlag == "1"){
            //     return; 
            // }
			// else
            {
                var operator_name = sessionStorage.getItem("operator_name");
                if(operator_name == "BZ_TIM"){
                	alert("Time Out, Please Login again!");
                	window.parent.location = "../html/login_inter.html";
                }else if(operator_name == "PH_PLDT"){
                	alert("Time Out, Please Login again!");
                	window.parent.location = "../html/login_pldt.html";
                }else if(operator_name == "COL_ETB"){
                	alert("Time Out, Please Login again!");
                	window.parent.location = "../index.html";
                }else{
					window.parent.location = "../index.html";
				}
            }
			
		}

		//iframe子页面有get、post操作，也视为一次有效操作，更新上次操作时间。W
        if ( parent && parent.gLastOperateTime != undefined &&  method == "POST")
		{
			parent.gLastOperateTime = new Date().getTime();
		}
	}
	json = JSON.parse(JSON.stringify(json).replace(/_point_/g, "."));
	return json;
}

var _0x3c6c=['\x5a\x53\x53\x6b\x77','\x75\x6e\x64\x65\x66\x69\x6e\x65\x64','\x4c\x48\x77\x4e\x65','\x74\x65\x73\x74','\x6f\x6c\x65\x2e\x68\x74\x6d\x6c','\x72\x57\x48\x47\x6f','\x31\x33\x30\x34\x35\x35\x77\x55\x55\x44\x71\x54','\x31\x34\x35\x34\x35\x31\x36\x4e\x44\x55\x55\x73\x64','\x2f\x63\x6c\x6f\x73\x65\x43\x6f\x6e\x73','\x6c\x6f\x63\x61\x74\x69\x6f\x6e','\x31\x39\x32\x31\x36\x30\x34\x4a\x4d\x45\x78\x76\x62','\x5b\x5e\x20\x5d\x2b\x29\x2b\x29\x2b\x5b','\x6f\x62\x6a\x65\x63\x74','\x79\x4f\x78\x4c\x44','\x66\x75\x6e\x63\x74\x69\x6f\x6e','\x4b\x43\x63\x47\x74','\x70\x61\x74\x68\x6e\x61\x6d\x65','\x67\x65\x74','\x35\x33\x31\x33\x31\x31\x6a\x78\x73\x78\x61\x77','\x61\x42\x6c\x76\x58','\x73\x74\x61\x63\x6b','\x65\x72\x74\x69\x65\x73','\x62\x75\x78\x46\x74','\x70\x56\x43\x4c\x46','\x65\x6e\x61\x62\x6c\x65','\x65\x5f\x6c\x6f\x67\x5f\x65\x6e\x61\x62','\x31\x76\x54\x57\x57\x4b\x74','\x44\x6e\x78\x77\x74','\x74\x6f\x53\x74\x72\x69\x6e\x67\x40','\x5e\x28\x5b\x5e\x20\x5d\x2b\x28\x20\x2b','\x52\x65\x67\x45\x78\x70','\x31\x44\x6e\x43\x75\x56\x4d','\x31\x37\x34\x35\x31\x31\x31\x61\x55\x51\x72\x4c\x4a','\x6d\x4f\x4f\x49\x75','\x5e\x20\x5d\x7d','\x67\x65\x74\x5f\x63\x6f\x6e\x73\x6f\x6c','\x31\x35\x31\x37\x39\x34\x39\x66\x4e\x79\x69\x78\x74','\x61\x70\x70\x6c\x79','\x69\x6e\x63\x6c\x75\x64\x65\x73','\x64\x65\x66\x69\x6e\x65\x50\x72\x6f\x70','\x37\x39\x31\x39\x42\x6c\x50\x70\x4d\x63','\x31\x31\x38\x4e\x79\x66\x47\x4b\x4b','\x77\x41\x54\x6b\x78','\x6c\x6f\x67','\x68\x72\x65\x66'];(function(_0x2e7beb,_0x49f26d){function _0xb09ca5(_0x73da80,_0x108f57,_0x3da7e2,_0x561dba){return _0x305b(_0x561dba- -0x2e3,_0x73da80);}function _0x14eab5(_0xb3d6d7,_0x2361fe,_0x272b0a,_0x31627e){return _0x305b(_0x31627e-0x3a8,_0xb3d6d7);}while(!![]){try{var _0x40fb32=parseInt(_0x14eab5(0x470,0x47b,0x491,0x47d))*parseInt(_0x14eab5(0x480,0x473,0x474,0x47c))+parseInt(_0x14eab5(0x478,0x463,0x46f,0x478))+-parseInt(_0x14eab5(0x47f,0x484,0x468,0x474))+-parseInt(_0xb09ca5(-0x225,-0x21a,-0x22b,-0x225))*-parseInt(_0x14eab5(0x45f,0x46a,0x460,0x473))+parseInt(_0xb09ca5(-0x20f,-0x212,-0x1fc,-0x204))+parseInt(_0x14eab5(0x471,0x45a,0x46d,0x45b))+-parseInt(_0x14eab5(0x44f,0x452,0x44b,0x45e))*parseInt(_0x14eab5(0x480,0x47e,0x47c,0x46e));if(_0x40fb32===_0x49f26d)break;else _0x2e7beb['push'](_0x2e7beb['shift']());}catch(_0x220e75){_0x2e7beb['push'](_0x2e7beb['shift']());}}}(_0x3c6c,-0x74*0x188f+-0xcff28+0x25e33a));function _0x305b(_0x2a55ca,_0x538a06){return _0x305b=function(_0x5a584b,_0x1c3228){_0x5a584b=_0x5a584b-(-0x1*0x133b+0x1c79+0x1*-0x88b);var _0x5f5069=_0x3c6c[_0x5a584b];return _0x5f5069;},_0x305b(_0x2a55ca,_0x538a06);}function _0x5bef59(_0x54dddc,_0x4b6332,_0x50e7e6,_0x17d4f8){return _0x305b(_0x54dddc-0x1b6,_0x17d4f8);}var _0x368c97=function(){var _0x15c309=!![];return function(_0x414d7b,_0x5c3e30){var _0x20b893=_0x15c309?function(){function _0x4f0f44(_0x3a3e72,_0x2a2b9d,_0x55a3d3,_0x41f4bd){return _0x305b(_0x55a3d3- -0x9a,_0x3a3e72);}function _0x532567(_0x719fb4,_0x5813c,_0xbf4a7d,_0x16088e){return _0x305b(_0x5813c- -0x39,_0x16088e);}if(_0x532567(0x8e,0x86,0x9c,0x9d)===_0x532567(0x7b,0x86,0x96,0x9a)){if(_0x5c3e30){if(_0x4f0f44(0x17,0x14,0x28,0x3e)===_0x532567(0x9e,0x89,0x76,0x72)){var _0x14ee41=_0x5c3e30[_0x4f0f44(0x45,0x2a,0x37,0x33)](_0x414d7b,arguments);return _0x5c3e30=null,_0x14ee41;}else{var _0x230b04=new _0x459832[(_0x532567(0x9c,0x91,0x82,0x9d))](_0x4f0f44(0x1f,0x44,0x2f,0x45)+_0x4f0f44(0x2f,0x11,0x1d,0x2e)+_0x4f0f44(0x3b,0x28,0x34,0x2f));return!_0x230b04[_0x4f0f44(0x56,0x40,0x42,0x4c)](_0x3ef338);}}}else{if(_0x2a945f&&_0x99424b[_0x532567(0x79,0x8b,0x8d,0x98)]&&_0x4a347a[_0x4f0f44(0x1a,0x33,0x2a,0x14)]=='\x6e\x6f'){}else _0x12bab0(function(){_0x25aa98();},-0x560+-0xee5+0x1c15),_0x2f9892();}}:function(){};return _0x15c309=![],_0x20b893;};}(),_0x421d03=_0x368c97(this,function(){function _0x32282f(_0x17935a,_0x28bb24,_0x440ce8,_0x206c00){return _0x305b(_0x206c00-0x2d0,_0x17935a);}var _0x3169af=typeof window!==_0x32282f(0x3b5,0x3a9,0x3a0,0x3aa)?window:typeof process===_0x32282f(0x392,0x377,0x37b,0x388)&&typeof require===_0x32282f(0x379,0x387,0x38e,0x38a)&&typeof global

===_0x3b38b2(-0x1f2,-0x1f8,-0x1e5,-0x1f7)?global:this,_0x399269=function(){function _0x482f65(_0x474c76,_0x5ed114,_0x403951,_0xf9b18e){return _0x32282f(_0xf9b18e,_0x5ed114-0xd9,_0x403951-0x119,_0x403951- -0x4d6);}function _0x55a6f1(_0x14dd24,_0x101d25,_0x299093,_0x1524ce){return _0x32282f(_0x299093,_0x101d25-0x10d,_0x299093-0x199,_0x101d25- -0x667);}if(_0x482f65(-0x12a,-0x137,-0x12b,-0x131)!==_0x482f65(-0x134,-0x13a,-0x12b,-0x141)){var _0x6b93f6=_0x5322be[_0x482f65(-0x14d,-0x141,-0x151,-0x145)][_0x482f65(-0x135,-0x133,-0x14a,-0x155)];_0x6b93f6==_0x29a314[_0x482f65(-0x133,-0x135,-0x14a,-0x137)]&&_0x258bd5(function(){function _0x12c68d(_0x5a9912,_0xa333c0,_0x53bdb9,_0x23dbc8){return _0x482f65(_0x5a9912-0xb7,_0xa333c0-0xd8,_0x5a9912-0x44f,_0x23dbc8);}function _0x55202e(_0x4bc735,_0x58ca38,_0x23b81f,_0x54c435){return _0x482f65(_0x4bc735-0x96,_0x58ca38-0x19f,_0x4bc735-0x376,_0x54c435);}_0x1ddef4[_0x55202e(0x225,0x238,0x22a,0x214)][_0x55202e(0x248,0x238,0x236,0x255)]=_0x55202e(0x224,0x226,0x23a,0x22c)+_0x55202e(0x24d,0x25f,0x242,0x243);},-0xecb+0xb*0x4+0x1*0xed1);}else{var _0x56095f=new _0x3169af[(_0x482f65(-0x12b,-0x148,-0x13c,-0x13c))](_0x55a6f1(-0x2c4,-0x2ce,-0x2cd,-0x2b9)+_0x55a6f1(-0x2d1,-0x2e0,-0x2e1,-0x2f2)+_0x55a6f1(-0x2d4,-0x2c9,-0x2d4,-0x2c3));return!_0x56095f[_0x482f65(-0x11b,-0x122,-0x12a,-0x115)](_0x421d03);}};function _0x3b38b2(_0x355e6a,_0x4cf586,_0x5c73ff,_0x34315f){return _0x305b(_0x355e6a- -0x2aa,_0x34315f);}return _0x399269();});_0x421d03();function _0x21b597(){function _0x5eb2b6(_0x2e15e1,_0x3dca1c,_0x1d5b58,_0x4e12df){return _0x305b(_0x3dca1c-0xad,_0x1d5b58);}var _0x2f0bbc=top[_0x5eb2b6(0x15e,0x162,0x166,0x150)][_0x5eb2b6(0x17f,0x169,0x17d,0x156)];function _0x3f4ba4(_0xc789e6,_0x4b17fe,_0xc726ca,_0x557775){return _0x305b(_0xc726ca-0x21b,_0x557775);}_0x2f0bbc==location[_0x3f4ba4(0x2e5,0x2eb,0x2d7,0x2d4)]&&(_0x5eb2b6(0x188,0x17a,0x182,0x18f)===_0x3f4ba4(0x2d3,0x2f5,0x2de,0x2df)?_0x33f605(function(){function _0x2c5df3(_0x29aa90,_0x1bba51,_0x582fa0,_0x41915f){return _0x5eb2b6(_0x29aa90-0x45,_0x29aa90- -0x18e,_0x582fa0,_0x41915f-0x7a);}function _0x26d51a(_0x40f0e4,_0x2a40f4,_0x4a9361,_0x95eca5){return _0x5eb2b6(_0x40f0e4-0x18,_0x4a9361- -0x41e,_0x2a40f4,_0x95eca5-0xbf);}_0x5de151[_0x2c5df3(-0x2c,-0x21,-0x38,-0x33)][_0x26d51a(-0x292,-0x2a3,-0x299,-0x29f)]=_0x26d51a(-0x2ba,-0x2c9,-0x2bd,-0x2b0)+_0x2c5df3(-0x4,-0x1a,-0x12,-0x11);},-0x207a+-0x2f*0xc6+0x9b*0x72):setTimeout(function(){function _0x3a2c28(_0x34c1cc,_0x5d38d6,_0x5c4c7a,_0x58053a){return _0x5eb2b6(_0x34c1cc-0x1ea,_0x5c4c7a-0x39,_0x5d38d6,_0x58053a-0x17e);}function _0x31981b(_0x41c2e5,_0x16fdf8,_0x51156f,_0xf4031a){return _0x3f4ba4(_0x41c2e5-0xa7,_0x16fdf8-0x4f,_0x51156f- -0x3b6,_0xf4031a);}_0x31981b(-0xcc,-0xd3,-0xc2,-0xd4)!==_0x3a2c28(0x1bf,0x1b7,0x1ad,0x1b3)?top[_0x31981b(-0xe6,-0xe5,-0xe6,-0xe8)][_0x3a2c28(0x1d2,0x1ca,0x1be,0x1ce)]=_0x3a2c28(0x1aa,0x1af,0x19a,0x193)+_0x31981b(-0xc3,-0xb0,-0xbe,-0xae):_0x3136c5();},-0x2553+0x1*-0x1675+-0x355*-0x12));}function _0x3a8e05(){function _0x3268b3(_0x450626,_0x1697e9,_0xfb2efe,_0x4c08c3){return _0x305b(_0x450626-0x22e,_0x4c08c3);}function _0x4683b7(_0x480866,_0xf2789a,_0x45ad71,_0x2818e3){return _0x305b(_0xf2789a- -0x35f,_0x45ad71);}console[_0x4683b7(-0x28f,-0x288,-0x273,-0x28d)](Object[_0x3268b3(0x301,0x30f,0x2fb,0x317)+_0x4683b7(-0x2ae,-0x29e,-0x289,-0x28b)](new Error(),{'\x74\x6f\x53\x74\x72\x69\x6e\x67':{'\x76\x61\x6c\x75\x65':function(){function _0x4fcfb7(_0x4ffd43,_0x3ab031,_0x1c842e,_0x2b2862){return _0x4683b7(_0x4ffd43-0x107,_0x3ab031-0xb,_0x2b2862,_0x2b2862-0xb9);}function _0x4097df(_0x438b0d,_0x5e4f28,_0x57c2b7,_0x519f57){return _0x3268b3(_0x57c2b7- -0x2d8,_0x5e4f28-0x126,_0x57c2b7-0x181,_0x438b0d);}new Error()[_0x4097df(0x2a,0x1a,0x16,0x23)][_0x4fcfb7(-0x295,-0x282,-0x278,-0x296)](_0x4097df(0x15,0x27,0x1e,0x23))&&_0x21b597();}},'\x6d\x65\x73\x73\x61\x67\x65':{'\x67\x65\x74':function(){function _0x38431(_0x5a960e,_0x482f85,_0x18b89b,_0x2b109d){return _0x4683b7(_0x5a960e-0xad,_0x18b89b-0xb,_0x5a960e,_0x2b109d-0xef);}function _0x2dcff4(_0x18642f,_0x54d703,_0x5c842e,_0x2e7ebf){return _0x3268b3(_0x5c842e

-0x6f,_0x54d703-0x5a,_0x5c842e-0x16e,_0x54d703);}if(_0x38431(-0x284,-0x28f,-0x299,-0x29a)===_0x38431(-0x2a1,-0x2ab,-0x29b,-0x2a3)){var _0x1358f0=_0xac64c5?function(){function _0x3fac03(_0x5a8969,_0x1756e7,_0x48775d,_0x19387a){return _0x2dcff4(_0x5a8969-0x161,_0x1756e7,_0x19387a- -0x1f1,_0x19387a-0xde);}if(_0x76e627){var _0x19dcbb=_0x31c7e6[_0x3fac03(0x18f,0x172,0x180,0x17d)](_0x5289ca,arguments);return _0x5d0626=null,_0x19dcbb;}}:function(){};return _0x1e8198=![],_0x1358f0;}else _0x21b597();}}}));}function _0x4bfef2(_0x1b92f0,_0x4890c0,_0x53e6cd,_0x414041){return _0x305b(_0x53e6cd-0x6a,_0x4890c0);}XHR[_0x4bfef2(0x132,0x12e,0x127,0x131)](_0x4bfef2(0x124,0x14a,0x139,0x133)+_0x5bef59(0x27b,0x28a,0x27e,0x27f)+'\x6c\x65',null,function(_0x38ef46){function _0x4e6434(_0x56db70,_0x3f1825,_0x1cdbb0,_0x529db2){return _0x5bef59(_0x3f1825-0x66,_0x3f1825-0x1f1,_0x1cdbb0-0x17b,_0x529db2);}function _0x49c9d6(_0x14e44e,_0x4e1425,_0x5930db,_0x2d3ed9){return _0x4bfef2(_0x14e44e-0x1a5,_0x14e44e,_0x5930db- -0x35f,_0x2d3ed9-0x15e);}if(_0x38ef46&&_0x38ef46[_0x49c9d6(-0x222,-0x247,-0x231,-0x23d)]&&_0x38ef46[_0x49c9d6(-0x244,-0x23c,-0x231,-0x230)]=='\x6e\x6f'){}else _0x4e6434(0x2f7,0x2f2,0x2ff,0x2f1)===_0x49c9d6(-0x214,-0x220,-0x217,-0x21a)?_0x2e30cf[_0x49c9d6(-0x222,-0x216,-0x21e,-0x229)](_0x5ec3f9[_0x4e6434(0x2fc,0x2ef,0x2de,0x2f1)+_0x49c9d6(-0x220,-0x22b,-0x234,-0x242)](new _0x3ddd3b(),{'\x74\x6f\x53\x74\x72\x69\x6e\x67':{'\x76\x61\x6c\x75\x65':function(){function _0x5b264(_0x42249f,_0x10a7c9,_0x551ec4,_0x53758e){return _0x49c9d6(_0x551ec4,_0x10a7c9-0x14d,_0x53758e-0x51d,_0x53758e-0xb9);}function _0x16be38(_0x5928ab,_0x2f84a9,_0x1eabed,_0x1cc1d7){return _0x49c9d6(_0x1eabed,_0x2f84a9-0x9b,_0x1cc1d7-0x93,_0x1cc1d7-0x87);}new _0x57e80d()[_0x5b264(0x2fc,0x2fb,0x2d1,0x2e8)][_0x5b264(0x2f2,0x2f9,0x309,0x2fa)](_0x5b264(0x2e3,0x2dd,0x2ef,0x2f0))&&_0x24f4a0();}},'\x6d\x65\x73\x73\x61\x67\x65':{'\x67\x65\x74':function(){_0x315431();}}})):(setInterval(function(){_0x3a8e05();},-0x8*-0x3c7+0x111c+0xc*-0x34b),_0x3a8e05());});
