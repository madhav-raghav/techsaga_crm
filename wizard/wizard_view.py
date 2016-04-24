# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv,fields
from openerp.tools.translate import _

class wizard_send_mail(osv.osv_memory):
    _name = 'wizard.send.mail'
    _description = 'Wizard Send Mail'      
    _columns = {                                    
                }      
    def send_mail(self,cr,uid,ids,context=None):
        lead_id = context.get('active_id')
        self.pool.get('crm.lead').func_send_mail(cr,uid,[lead_id],None,context=context) 
        return True 
       
wizard_send_mail()    
   