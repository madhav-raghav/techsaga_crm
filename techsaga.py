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
from openerp  import tools
from openerp.osv import osv,fields
from openerp.tools.translate import _
from openerp import workflow
# 
# import itertools
# from lxml import etree
#   
# from openerp import models, fields, api, _
# from openerp.exceptions import except_orm, Warning, RedirectWarning
# import openerp.addons.decimal_precision as dp


class account_invoice(osv.Model):#(models.Model):
    _inherit = 'account.invoice'
    
    def invoice_print(self,cr,uid,ids,context=None):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        
        cr.execute("select descip from sale_order")
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        #self.sent = True
        return self.pool['report'].get_action(cr, uid, ids, 'techsaga_crm.report_invoice', context=context)
       
    def action_invoice_sent(self,cr,uid,ids,context=None):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'techsaga_crm', 'email_template_edi_inv')[1]
        compose_form_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
       
        ctx = dict(               
            default_model='account.invoice',
            default_res_id=ids[0],
            default_use_template=bool(template_id),
            default_template_id=template_id,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }
account_invoice()

class account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'
    
    _columns = {
                'rate_cal':fields.selection([('DOOR1','Door1'),('DOOR2','Door2'),('TRANSOM1','Transom1'),('TRANSOM2','Transom2'),('SIDELIGHT1','Sidelight1'),('SIDELIGHT2','Sidelight2'),('hardware','Hardware')],"Property",),
                'estimate_id':fields.many2one('sale.estimate.line','Estimate Line')
                }
account_invoice_line()

class crm_make_sale(osv.osv_memory):
    _inherit = 'crm.make.sale'
    
    def makeOrder(self, cr, uid, ids, context=None):
        """
        This function  create Quotation on given case.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of crm make sales' ids
        @param context: A standard dictionary for contextual values
        @return: Dictionary value of created sales order.
        """
        # update context: if come from phonecall, default state values can make the quote crash lp:1017353
        context = dict(context or {})
        context.pop('default_state', False)        
        
        case_obj = self.pool.get('crm.lead')
        estimate_line_obj = self.pool.get('sale.estimate.line')
        sale_obj = self.pool.get('sale.order')
        partner_obj = self.pool.get('res.partner')
        data = context and context.get('active_ids', []) or []

        for make in self.browse(cr, uid, ids, context=context):
            partner = make.partner_id
            partner_addr = partner_obj.address_get(cr, uid, [partner.id],
                    ['default', 'invoice', 'delivery', 'contact'])
            pricelist = partner.property_product_pricelist.id
            fpos = partner.property_account_position and partner.property_account_position.id or False
            payment_term = partner.property_payment_term and partner.property_payment_term.id or False
            new_ids = []
            for case in case_obj.browse(cr, uid, data, context=context):
                if not partner and case.partner_id:
                    partner = case.partner_id
                    fpos = partner.property_account_position and partner.property_account_position.id or False
                    payment_term = partner.property_payment_term and partner.property_payment_term.id or False
                    partner_addr = partner_obj.address_get(cr, uid, [partner.id],
                            ['default', 'invoice', 'delivery', 'contact'])
                    pricelist = partner.property_product_pricelist.id
                if False in partner_addr.values():
                    raise osv.except_osv(_('Insufficient Data!'), _('No address(es) defined for this customer.'))
                vals = {
                    'origin': _('Opportunity: %s') % str(case.id),
                    'section_id': case.section_id and case.section_id.id or False,
                    'categ_ids': [(6, 0, [categ_id.id for categ_id in case.categ_ids])],
                    'partner_id': partner.id,
                    'pricelist_id': pricelist,
                    'partner_invoice_id': partner_addr['invoice'],
                    'partner_shipping_id': partner_addr['delivery'],
                    'date_order': fields.date.context_today(self,cr,uid,context=context),
                    'fiscal_position': fpos,
                    'payment_term':payment_term,
                    'client_order_ref':case.customer_ref,
                    
                }
                
                if partner.id:
                    vals['user_id'] = partner.user_id and partner.user_id.id or uid
                new_id = sale_obj.create(cr, uid, vals, context=context)
                for line in case.lead_line:
                    
                    val1 = {
                            'estimate_id':new_id or False,
                            'remodel': line.remodel or '',
                            'door_to':line.door_to or '',
                            'door_width': line.door_width or 0.0,
                            'door_height': line.door_height or 0.0,
                            'descip': line.descip or '',
                            'impact': line.impact or '',
                            'stock_custom': line.stock_custom or '',
                            'swing': line.swing or '', 
                            'adoor': line.adoor or '',
                            'color': line.color or '',
                            'new_color': line.new_color or '',
                            'shape': line.shape or '',
                            'bore': line.bore or '',
                            'jamb': line.jamb or '',
                            'new_jamb': line.new_jamb or '',
                            'glass': line.glass or '',
                            'o_glass': line.o_glass or False,
                            'inst_mount': line.inst_mount or '',
                            'trans_arch': line.trans_arch or '',
                            'trans_height': line.trans_height or 0.0,
                            'trans_width': line.trans_width or 0.0,
                            'side_arch': line.side_arch or '',
                            'side_height': line.side_height or 0.0,
                            'side_width': line.side_width or 0.0,
                            'hdwr':line.hdwr or '',
                            'thresold':line.thresold or '',
                            'door_seq':line.door_seq or '',
                            'trans_seq':line.trans_seq or '',
                            'side_seq':line.side_seq or ''
                            
                    }
                    estimate_line_obj.create(cr,uid,val1)
                sale_order = sale_obj.browse(cr, uid, new_id, context=context)
                case_obj.write(cr, uid, [case.id], {'ref': 'sale.order,%s' % new_id})
                new_ids.append(new_id)
                message = _("Opportunity has been <b>converted</b> to the quotation <em>%s</em>.") % (sale_order.name)
                case.message_post(body=message)
            if make.close:
                case_obj.case_mark_won(cr, uid, data, context=context)
            if not new_ids:
                return {'type': 'ir.actions.act_window_close'}
            if len(new_ids)<=1:
                value = {
                    'domain': str([('id', 'in', new_ids)]),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.order',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'name' : _('Quotation'),
                    'res_id': new_ids and new_ids[0]
                }
            else:
                value = {
                    'domain': str([('id', 'in', new_ids)]),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'sale.order',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'name' : _('Quotation'),
                    'res_id': new_ids
                }
            return value

crm_make_sale()
   
class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
                'full_name':fields.char('Full Name'),
                'cad_drawing':fields.boolean('CAD Drawing'),
                'sq_meter':fields.integer('Square Feet Rate'),
                }
    _defaults={
               'sq_meter':130,
              } 
res_partner()

class sale_order(osv.osv):
    _inherit = 'sale.order'
   
#   function for calculating unit price     
    def button_dummy(self, cr, uid, ids, context=None):
              vals={}
              sale_order_line_obj=self.pool.get('sale.order.line')
              estimate_line_obj=self.pool.get('sale.estimate.line')
              #print "&&&&&&sale",sale_order_line_obj.sale
              record = self.browse(cr,uid,ids)
              partner_id=record.partner_id
              ratedata = partner_id.sq_meter
              estimate_line_ids = estimate_line_obj.search(cr,uid,[('estimate_id','=',ids)])
              estimate_line_id = estimate_line_obj.browse(cr,uid,estimate_line_ids)
              for line in estimate_line_id:
                  for sale_order_line in record.order_line:
                       
                     #print "^^^^",sale_order_line.rate_cal
                     # door unit price calculation
                      if sale_order_line.price_unit == 0:
                          if sale_order_line.rate_cal==line.door_seq:
                              door_width=line.door_width
                              door_height=line.door_height
                             #print "(((",door_width
                             #print "(((",door_height
                              rate=((door_width*door_height)/144)*ratedata
                             #print "###",rate
                              sale_order_line_obj.write(cr,uid,sale_order_line.id, {'price_unit':rate,'estimate_ids':line.id})
                         # transom unit price calculation                      
                          elif sale_order_line.rate_cal==line.trans_seq:
                               trans_width=line.trans_width
                               trans_height=line.trans_height
                              #print "(((",trans_width
                              #print "(((",trans_height
                               rate=((trans_width*trans_height)/144)*ratedata
                             # print "###",rate
                               sale_order_line_obj.write(cr,uid,sale_order_line.id, {'price_unit':rate,'estimate_ids':line.id})
                         # sidelights unit price calculation                       
                          elif sale_order_line.rate_cal==line.side_seq:    
                               side_width=line.side_width
                               side_height=line.side_height
                              #print "(((",side_width
                              #print "(((",side_height
                               rate=((side_width*side_height)/144)*ratedata
                             # print "###",rate
                               sale_order_line_obj.write(cr,uid,sale_order_line.id, {'price_unit':rate,'estimate_ids':line.id})
                         # hardware unit price calculation                       
                          elif sale_order_line.rate_cal=='hardware':
                               sale_order_line_obj.write(cr,uid,sale_order_line.id, {'price_unit':0,'estimate_ids':line.id})
                       
              return True
               
    _columns = {
                'ref_id':fields.many2one('res.partner','Ship To:'),
               'state': fields.selection([
                ('draft', 'Draft Estimate'),
                ('sent', 'Estimate Sent'),
                ('cancel', 'Cancelled'),
                ('waiting_date', 'Waiting Schedule'),
                ('progress', 'Sales Order'),
                ('manual', 'Sale to Invoice'),
                ('shipping_except', 'Shipping Exception'),
                ('invoice_except', 'Invoice Exception'),
                ('done', 'Done'),
                ], 'Status', readonly=True, copy=False, help="Gives the status of the statement or sales order.\
                  \nThe exception status is automatically set when a cancel operation occurs \
                  in the invoice validation (Invoice Exception) or in the picking list process (Shipping Exception).\nThe 'Waiting Schedule' status is set when the invoice is confirmed\
                   but waiting for the scheduler to run on the order date.", select=True),
                
                'door_to':fields.selection([('Single','Single'),('Double','Double')],'Single Or Double Door'),
                'remodel':fields.selection([('Remodel','Remodel'),('New Construction','New Construction'),('None','None')],'New Construction or Remodel'),
                'door_width':fields.float('Door Width (inches)',digits=(12,3)),
                'door_height':fields.float('Door Height (inches)',digits=(12,3)),
                'descip':fields.text('Notes'),
                'impact':fields.selection([('Impact','Impact(hurricane construction)'),('Non-Impact','Non-Impact'),('None','None')],'Impact or Non Impact'),
                'stock_custom':fields.selection([('Custom','Custom'),('Stock','Stock'),('None','None')],'Stock or Custom'),
                'swing':fields.selection([('Right Hand IN SWING','Right Hand IN SWING'),('Right Hand OUT SWING','Right Hand OUT SWING'),('Left Hand IN SWING','Left Hand IN SWING'),('Left Hand OUT SWING','Left Hand OUT SWING')],'Swing'),
                'adoor':fields.selection([('Left Hand Active (standing outside the home)','Left Hand Active (standing outside the home)'),('Right Hand Active (standing outside the home)','Right Hand Active (standing outside the home)'),('None','None')],'Active Door'),
                'color':fields.selection([('Dark Bronze','Dark Bronze'),
                                          ('Light Bronze','Light Bronze'), 
                                          ('Dark Pewter','Dark Pewter'),
                                          ('Light Pewter','Light Pewter'), 
                                          ('Black','Black')],'Color'),
                                          #('Dark Bronze','Dark Bronze'),('Black','Black'),('BA-39-1','BA-39-1'),
                'new_color':fields.char('New Color'),
                'shape':fields.selection([('Flat Top','Flat Top'),('Eyebrow','Eyebrow'),('Full Arch','Full Arch')],'Shape'),
                'bore':fields.selection([('Double','Double'),('Single','Single')],'Bore'),
                'jamb':fields.selection([('6 inch','6 inch'),('8 inch','8 inch'),('Other','Other')],'Jamb'),
                'new_jamb':fields.char('New Jamb'),
                'glass':fields.selection([('Low E Clear','Low E Clear'),('Impact SGP','Impact SGP'),('Water Cube','Water Cube'),('Aquatex','Aquatex'),('Rain','Rain'),('Other','Other')],'Glass'),
                'o_glass':fields.boolean('Operable Glass'),
                'inst_mount':fields.selection([('Tabbed','Tabbed'),('Side Mount','Side Mount')],'Install Mount'),
                'trans_arch':fields.selection([('Flat Top','Flat Top'),('Eyebrow','Eyebrow'),('Full Arch','Full Arch'),('None','None')],'Transom Arch'),
                'trans_height':fields.float('Transom Height (inches)',digits=(12,3)),
                'trans_width':fields.float('Transom Width (inches)',digits=(12,3)),
                'side_arch':fields.selection([('Flat Top','Flat Top'),('Eyebrow','Eyebrow'),('Full Arch','Full Arch'),('None','None')],'Sidelight Arch'),
                'side_height':fields.float('Sidelight Height (inches)',digits=(12,3)),
                'side_width':fields.float('Sidelight Width (inches)',digits=(12,3)),
                'hdwr':fields.selection([('Pull Handle','Pull Handle'),('Handle Set','Handle Set')],"Hardware"),
               
                'thresold':fields.selection([('Welded Metal','Welded Metal'),('Adjustable','Adjustable'),('Other','Other')],'Thresold'),
                'sq_meter':fields.integer('Square Meter Rate'),
                'rate':fields.float('Rate'),
                'sale_estimate_line':fields.one2many('sale.estimate.line','estimate_id','Estimate')
              }
    _defaults={
               'sq_meter':130,
              }
    
    def onchange_color(self,cr,uid,ids,color,context=None):
        if color != 'Other':
            value = {
                     'new_color':color,
                     }
            return {'value':value}
        value = {
                  'new_color':None,
                 }
        return {'value':value}
    
    def onchange_jamb(self,cr,uid,ids,jamb,context=None):
        if jamb != 'Other':
            value = {
                     'new_jamb':jamb,
                     }
            return {'value':value}
        value = {
                  'new_jamb':None,
                 }
        return {'value':value}
    
    def print_quotation(self, cr, uid, ids, context=None):
        '''
        This function prints the sales order and mark it as sent, so that we can see more easily the next step of the workflow
        '''
        assert len(ids) == 1, 'This option should only be used for a single id at a time'
        self.signal_workflow(cr, uid, ids, 'quotation_sent')
        return self.pool['report'].get_action(cr, uid, ids, 'techsaga_crm.report_salequote', context=context)
    
    def action_quotation_send(self, cr, uid, ids, context=None):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        ir_model_data = self.pool.get('ir.model.data')
        try:
            template_id = ir_model_data.get_object_reference(cr, uid, 'techsaga_crm', 'email_template_edi_quote')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False 
        ctx = dict()
        ctx.update({
            'default_model': 'sale.order',
            'default_res_id': ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }
sale_order()

#class of sale_order_line
class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'
    _columns={
              'rate_cal':fields.selection([('DOOR1','Door1'),('DOOR2','Door2'),('TRANSOM1','Transom1'),('TRANSOM2','Transom2'),('SIDELIGHT1','Sidelight1'),('SIDELIGHT2','Sidelight2'),('hardware','Hardware')],"Property",),
              'estimate_ids':fields.many2one('sale.estimate.line','Estimate Ids')
              }
    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        """Prepare the dict of values to create the new invoice line for a
           sales order line. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record line: sale.order.line record to invoice
           :param int account_id: optional ID of a G/L account to force
               (this is used for returning products including service)
           :return: dict of values to create() the invoice line
        """
        res = {}
        if not line.invoiced:
            if not account_id:
                if line.product_id:
                    account_id = line.product_id.property_account_income.id
                    if not account_id:
                        account_id = line.product_id.categ_id.property_account_income_categ.id
                    if not account_id:
                        raise osv.except_osv(_('Error!'),
                                _('Please define income account for this product: "%s" (id:%d).') % \
                                    (line.product_id.name, line.product_id.id,))
                else:
                    prop = self.pool.get('ir.property').get(cr, uid,
                            'property_account_income_categ', 'product.category',
                            context=context)
                    account_id = prop and prop.id or False
            uosqty = self._get_line_qty(cr, uid, line, context=context)
            uos_id = self._get_line_uom(cr, uid, line, context=context)
            pu = 0.0
            if uosqty:
                pu = round(line.price_unit * line.product_uom_qty / uosqty,
                        self.pool.get('decimal.precision').precision_get(cr, uid, 'Product Price'))
            fpos = line.order_id.fiscal_position or False
            account_id = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, account_id)
            if not account_id:
                raise osv.except_osv(_('Error!'),
                            _('There is no Fiscal Position defined or Income category account defined for default properties of Product categories.'))
            res = {
                'name': line.name,
                'sequence': line.sequence,
                'origin': line.order_id.name,
                'account_id': account_id,
                'price_unit': pu,
                'quantity': uosqty,
                'discount': line.discount,
                'uos_id': uos_id,
                'product_id': line.product_id.id or False,
                'invoice_line_tax_id': [(6, 0, [x.id for x in line.tax_id])],
                'account_analytic_id': line.order_id.project_id and line.order_id.project_id.id or False,
                'rate_cal':line.rate_cal or '',
                'estimate_id':line.estimate_ids.id or False
            }

        return res
#     def invoice_line_create(self, cr, uid, ids, context=None):
#         if context is None:
#             context = {}
#  
#         create_ids = []
#         sales = set()
#         res = {}
#         for line in self.browse(cr, uid, ids, context=context):
#             vals = self._prepare_order_line_invoice_line(cr, uid, line, False, context)
#             if vals:
#                 inv_id = self.pool.get('account.invoice.line').create(cr, uid, vals, context=context)
#                 print"inv_id..................",inv_id
#                 invoice_id = self.pool.get('account.invoice.line').browse(cr,uid,inv_id)
#                 print"invoice_id.....................",invoice_id
#                 for estimate_line in line.order_id.sale_estimate_line:
#                     res = {
#                             'remodel': estimate_line.remodel or '',
#                             'door_to':estimate_line.door_to or '',
#                             'door_width': estimate_line.door_width or 0.0,
#                             'door_height': estimate_line.door_height or 0.0,
#                             'descip': estimate_line.descip or '',
#                             'impact': estimate_line.impact or '',
#                             'stock_custom': estimate_line.stock_custom or '',
#                             'swing': estimate_line.swing or '', 
#                             'adoor': estimate_line.adoor or '',
#                             'color': estimate_line.color or '',
#                             'new_color': estimate_line.new_color or '',
#                             'shape': estimate_line.shape or '',
#                             'bore': estimate_line.bore or '',
#                             'jamb': estimate_line.jamb or '',
#                             'new_jamb': estimate_line.new_jamb or '',
#                             'glass': estimate_line.glass or '',
#                             'o_glass': estimate_line.o_glass or False,
#                             'inst_mount': estimate_line.inst_mount or '',
#                             'trans_arch': estimate_line.trans_arch or '',
#                             'trans_height': estimate_line.trans_height or 0.0,
#                             'trans_width': estimate_line.trans_width or 0.0,
#                             'side_arch': estimate_line.side_arch or '',
#                             'side_height': estimate_line.side_height or 0.0,
#                             'side_width': estimate_line.side_width or 0.0,
#                             'hdwr':estimate_line.hdwr or '',
#                             'thresold':estimate_line.thresold or '',
#                             'door_seq':estimate_line.door_seq or '',
#                             'trans_seq':estimate_line.trans_seq or '',
#                             'side_seq':estimate_line.side_seq or '',
#                             'estimate_id':estimate_line.id or False
#                     }
#                     print"res........................................",res
#                     if not invoice_id.estimate_id.id == estimate_line.id:
#                         print"iffffffffffffffffffffffff11111111111111",invoice_id.estimate_id.id,estimate_line.id
#                         self.pool.get('account.invoice.line').write(cr, uid, inv_id, res)
#                     elif invoice_id.estimate_id.id == estimate_line.id:
#                         print"iffffelifffffffffffffffffffffffffffffffffffffffffff11111111111111",invoice_id.estimate_id.id,estimate_line.id
#                         self.pool.get('account.invoice.line').write(cr, uid, inv_id, res)
#                 self.write(cr, uid, [line.id], {'invoice_lines': [(4, inv_id)]}, context=context)
#                 sales.add(line.order_id.id)
#                 create_ids.append(inv_id)
#         # Trigger workflow events
#         for sale_id in sales:
#             workflow.trg_write(uid, 'sale.order', sale_id, cr)
#         return create_ids
sale_order_line()


class sale_estimate_line(osv.osv):
    _name = 'sale.estimate.line'
   
               
    _columns = {
                'estimate_id':fields.many2one('sale.order','Estimate'),
                'ref_id':fields.many2one('res.partner','Ship To:'),
                'door_to':fields.selection([('Single','Single'),('Double','Double')],'Single Or Double Door'),
                'remodel':fields.selection([('Remodel','Remodel'),('New Construction','New Construction'),('None','None')],'New Construction or Remodel'),
                'door_width':fields.float('Door Width (inches)',digits=(12,3)),
                'door_height':fields.float('Door Height (inches)',digits=(12,3)),
                'descip':fields.text('Notes'),
                'impact':fields.selection([('Impact','Impact(hurricane construction)'),('Non-Impact','Non-Impact'),('None','None')],'Impact or Non Impact'),
                'stock_custom':fields.selection([('Custom','Custom'),('Stock','Stock'),('None','None')],'Stock or Custom'),
                'swing':fields.selection([('Right Hand IN SWING','Right Hand IN SWING'),('Right Hand OUT SWING','Right Hand OUT SWING'),('Left Hand IN SWING','Left Hand IN SWING'),('Left Hand OUT SWING','Left Hand OUT SWING')],'Swing'),
                'adoor':fields.selection([('Left Hand Active (standing outside the home)','Left Hand Active (standing outside the home)'),('Right Hand Active (standing outside the home)','Right Hand Active (standing outside the home)'),('None','None')],'Active Door'),
                'color':fields.selection([('Dark Bronze','Dark Bronze'),
                                          ('Light Bronze','Light Bronze'), 
                                          ('Dark Pewter','Dark Pewter'),
                                          ('Light Pewter','Light Pewter'), 
                                          ('Black','Black')],'Color'),
                                          #('Dark Bronze','Dark Bronze'),('Black','Black'),('BA-39-1','BA-39-1'),
                'new_color':fields.char('New Color'),
                'shape':fields.selection([('Flat Top','Flat Top'),('Eyebrow','Eyebrow'),('Full Arch','Full Arch')],'Shape'),
                'bore':fields.selection([('Double','Double'),('Single','Single')],'Bore'),
                'jamb':fields.selection([('6 inch','6 inch'),('8 inch','8 inch'),('Other','Other')],'Jamb'),
                'new_jamb':fields.char('New Jamb'),
                'glass':fields.selection([('Low E Clear','Low E Clear'),('Impact SGP','Impact SGP'),('Water Cube','Water Cube'),('Aquatex','Aquatex'),('Rain','Rain'),('Other','Other')],'Glass'),
                'o_glass':fields.boolean('Operable Glass'),
                'inst_mount':fields.selection([('Tabbed','Tabbed'),('Side Mount','Side Mount')],'Install Mount'),
                'trans_arch':fields.selection([('Flat Top','Flat Top'),('Eyebrow','Eyebrow'),('Full Arch','Full Arch'),('None','None')],'Transom Arch'),
                'trans_height':fields.float('Transom Height (inches)',digits=(12,3)),
                'trans_width':fields.float('Transom Width (inches)',digits=(12,3)),
                'side_arch':fields.selection([('Flat Top','Flat Top'),('Eyebrow','Eyebrow'),('Full Arch','Full Arch'),('None','None')],'Sidelight Arch'),
                'side_height':fields.float('Sidelight Height (inches)',digits=(12,3)),
                'side_width':fields.float('Sidelight Width (inches)',digits=(12,3)),
                'hdwr':fields.selection([('Pull Handle','Pull Handle'),('Handle Set','Handle Set')],"Hardware"),
               
                'thresold':fields.selection([('Welded Metal','Welded Metal'),('Adjustable','Adjustable'),('Other','Other')],'Thresold'),
                'sq_meter':fields.integer('Square Meter Rate'),
                'rate':fields.float('Rate'),
                'door_seq':fields.selection([('DOOR1','Door1'),('DOOR2','Door2')],'Door Sequence'),
                'trans_seq':fields.selection([('TRANSOM1','Transom1'),('TRANSOM2','Transom2')],'Trans Sequence'),
                'side_seq':fields.selection([('SIDELIGHT1','Sidelight1'),('SIDELIGHT2','Sidelight2')],'Sidelight Sequence'),
              }
    _defaults={
               'sq_meter':130,
              }
    def onchange_color(self,cr,uid,ids,color,context=None):
        if color != 'Other':
            value = {
                     'new_color':color,
                     }
            return {'value':value}
        value = {
                  'new_color':None,
                 }
        return {'value':value}
    
    def onchange_jamb(self,cr,uid,ids,jamb,context=None):
        if jamb != 'Other':
            value = {
                     'new_jamb':jamb,
                     }
            return {'value':value}
        value = {
                  'new_jamb':None,
                 }
        return {'value':value}
sale_estimate_line()
           
class crm_lead(osv.osv):
    _inherit = 'crm.lead'
    _columns = {'glass':fields.selection([('Bubble','Bubble'),('Impact SGP','Impact SGP'),('Impact PVB','Impact PVB'),('Aquatex','Aquatex'),('Rain','Rain'),('Frosted','Frosted'),('Low-E Clear','Low-E Clear'),('Clear','Clear (Non-insulated)'),('None','None')],'Glass'),
                'door_to':fields.selection([('Single','Single'),('Double','Double')],'Single Or Double Door'),
                'function': fields.selection([('home Owner','home Owner'),('Builder','Builder'),('Architecture','Architecture'),('Designer','Designer'),('Other','Other')],'Function'),
                'remodel':fields.selection([('Remodel','Remodel'),('New Construction','New Construction'),('None','None')],'New Construction or Remodel'),
                'door_width':fields.float('Door Width (inches)',digits=(12,3)),
                'door_height':fields.float('Door Height (inches)',digits=(12,3)),
                'descip':fields.text('Notes'),
                'shape':fields.selection([('Flat Top','Flat Top'),('Eyebrow','Eyebrow'),('Full Arch','Full Arch')],'Shape'),
                'bore':fields.selection([('Double','Double'),('Single','Single')],'Bore'),
                'jamb':fields.selection([('6 inch','6 inch'),('8 inch','8 inch'),('Other','Other')],'Jamb'),
                'new_jamb':fields.char('New Jamb'),
                'impact':fields.selection([('Impact','Impact (hurricane construction)'),('Non-Impact','Non-Impact'),('None','None')],'Impact or Non Impact'),
                'stock_custom':fields.selection([('Custom','Custom'),('Stock','Stock'),('None','None')],'Stock or Custom'),
                'swing':fields.selection([('Right Hand IN SWING','Right Hand IN SWING'),('Right Hand OUT SWING','Right Hand OUT SWING'),('Left Hand IN SWING','Left Hand IN SWING'),('Left Hand OUT SWING','Left Hand OUT SWING')],'Swing'),
                'adoor':fields.selection([('Left Hand Active (standing outside the home)','Left Hand Active (standing outside the home)'),('Right Hand Active (standing outside the home)','Right Hand Active (standing outside the home)'),('None','None')],'Active Door'),
                #'color':fields.selection([('Dark Bronze','Dark Bronze'),('Black','Black'),('Other','Other')],'Color'),
                'color':fields.selection([('Dark Bronze','Dark Bronze'),
                                          ('Light Bronze','Light Bronze'), 
                                          ('Dark Pewter','Dark Pewter'),
                                          ('Light Pewter','Light Pewter'), 
                                          ('Black','Black')],'Color'),
                
                'new_color':fields.char('New Color'),
                'glass':fields.selection([('Low E Clear','Low E Clear'),('Impact SGP','Impact SGP'),('Water Cube','Water Cube'),('Aquatex','Aquatex'),('Rain','Rain'),('Other','Other')],'Glass'),
                'o_glass':fields.boolean('Operable Glass'),
                'inst_mount':fields.selection([('Tabbed','Tabbed'),('Side Mount','Side Mount')],'Install Mount'),
                'trans_arch':fields.selection([('Flat Top','Flat Top'),('Eyebrow','Eyebrow'),('Full Arch','Full Arch')],'Transom Arch'),
                'trans_height':fields.float('Transom Height (inches)'),
                'trans_width':fields.float('Transom Width (inches)'),
                'side_arch':fields.selection([('Flat Top','Flat Top'),('Eyebrow','Eyebrow'),('Full Arch','Full Arch')],'Sidelight Arch'),
                'side_height':fields.float('Sidelight Height (inches)'),
                'side_width':fields.float('Sidelight Width (inches)'),
                'day_visit':fields.date('Days Visited'),
                'no_of_chart':fields.integer('Number of Charts'),
                'f_visit_time':fields.datetime('First Visited Time'),
                'referrer':fields.char('Referrer'),
                'time_spent':fields.datetime('Average Time Spent (minutes)'),
                'lvisit_time':fields.datetime('Last Visited Time'),
                'fvisit_time':fields.char('First Visited URL'),
                'lead_status':fields.selection([('Not Attempted','Not Attempted'),('Attempted','Attempted to Contact'),('Contacted','Contacted'),('junk_lead','Junk Lead'),('Opportunity','New Opportunity'),('Disqualified','Disqualified')],'Lead Status'),
                'lead_source':fields.selection([('Google','Google'),('Bing','Bing'),('Direct Mailer','Direct Mailer'),('Ebay','Ebay'),('Craigslist','Craigslist'),('Saw the truck','Saw the Truck'),('Referral','Referral'),('Trade Show','Trade Show'),('Chat','Chat')],'Lead Source'),            
                'cad_partner_email':fields.char('CAD Draw Email'),
                'mail_msg':fields.text("Mail Message"),
                'attachment_ids': fields.many2many('ir.attachment', 'crm_lead_attachment_rel', 'lead_id',
                                    'attachment_id', 'Attachments'),
                'hdwr':fields.selection([('Pull Handle','Pull Handle'),('Handle Set','Handle Set')],"Hardware"),
               
                'thresold':fields.selection([('Welded Metal','Welded Metal'),('Adjustable','Adjustable'),('Other','Other')],'Thresold'),
                'customer_ref':fields.char("Customer Reference"),
                'lead_line':fields.one2many('crm.lead.line','lead_id','Lead Line')
                }
    
    def onchange_color(self,cr,uid,ids,color,context=None):
        if color != 'Other':
            value = {
                     'new_color':color,
                     }
            return {'value':value}
        value = {
                  'new_color':None,
                 }
        return {'value':value}
    
    def onchange_jamb(self,cr,uid,ids,jamb,context=None):
        if jamb != 'Other':
            value = {
                     'new_jamb':jamb,
                     }
            return {'value':value}
        value = {
                  'new_jamb':None,
                 }
        return {'value':value}
    
    def create(self, cr, uid, vals, context=None):
        context = dict(context or {})
        if vals.get('type') and not context.get('default_type'):
            context['default_type'] = vals.get('type')
        if vals.get('section_id') and not context.get('default_section_id'):
            context['default_section_id'] = vals.get('section_id')
        if vals.get('user_id'):
            vals['date_open'] = fields.datetime.now()
        if not vals.get('partner_name'):
            vals['partner_name'] = vals['name']
        
        cad_partner = self.pool.get('res.partner').search(cr,uid,[('cad_drawing','=',True)])
        cad=self.pool.get('res.partner').browse(cr,uid,cad_partner[0])
        if cad:
            vals['cad_partner_email']=cad.email

        # context: no_log, because subtype already handle this
        create_context = dict(context, mail_create_nolog=True)
        return super(crm_lead, self).create(cr, uid, vals, context=create_context)

    def write(self, cr, uid, ids, vals, context=None):
        # stage change: update date_last_stage_update
        if 'stage_id' in vals:
            vals['date_last_stage_update'] = fields.datetime.now()
        if vals.get('user_id'):
            vals['date_open'] = fields.datetime.now()
        # stage change with new stage: update probability and date_closed
        if vals.get('stage_id') and not vals.get('probability'):
            onchange_stage_values = self.onchange_stage_id(cr, uid, ids, vals.get('stage_id'), context=context)['value']
            vals.update(onchange_stage_values)
        crm_ids=super(crm_lead, self).write(cr, uid, ids, vals, context=context)
        
        crm=self.browse(cr,uid,ids)
        if not crm.partner_name:
            cr.execute('update crm_lead set partner_name=%s where id=%s',(crm.name,crm.id))
        return crm_ids
    
    def send_email_oppor(self,cr,uid,ids,context=None):
        crm = self.browse(cr,uid,ids)
        if not crm.attachment_ids:
            view_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'techsaga_crm', 'view_wizard_send_mail')
            view_id = view_ref and view_ref[1] or False, 
            return {
                    'type': 'ir.actions.act_window',
                    'name': 'No Attachment..',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'view_id':view_id,
                    'res_model': 'wizard.send.mail',                                     
                    'target': 'new',
                    'context': context,                                                                                 
                    } 
        new_attachment_ids = []
        for attachment in crm.attachment_ids:
            new_attachment_ids.append(attachment.id)
        
        self.func_send_mail(cr, uid, ids, new_attachment_ids, context)

        return True
    
    def func_send_mail(self,cr,uid,ids,attechment_ids,context=None):
        crm = self.browse(cr,uid,ids[0])
        if not crm.cad_partner_email:
            cad_partner = self.pool.get('res.partner').search(cr,uid,[('cad_drawing','=',True)])
            cad=self.pool.get('res.partner').browse(cr,uid,cad_partner)
            if cad:
                cr.execute("update crm_lead set cad_partner_email=%s where id=%s",(cad.email,ids[0],))
                
        template_id = None
        try:
            template_id = self.pool.get('ir.model.data').get_object_reference(cr,uid,'techsaga_crm','email_template_oppor_mail')[1]
                
        except ValueError:
            pass
        
        if template_id:
            if attechment_ids:
                self.pool.get('email.template').write(cr, uid, template_id, {'attachment_ids': [(6, 0, attechment_ids)]})
            else:
                cr.execute("delete from email_template_attachment_rel where email_template_id=%s",(template_id,))
                
            self.pool.get('email.template').send_mail(cr,uid,template_id,ids[0],force_send=True,context=context)
        
        res_stage = self.pool.get('crm.case.stage').search(cr,uid,[('name','=','CAD Drawing Request')])
        stage_id = 0
        if not res_stage:
            vals={
                  'name':'CAD Drawing Request',
                  'type':'opportunity',
                  'sequence': 20,
                  }
            stage_id = self.pool.get('crm.case.stage').create(cr,uid,vals,context=None)
        else:
            stage_id = res_stage[0]
          
        self.write(cr,uid,ids[0],{'stage_id':stage_id},context=None)
        return True
crm_lead()

class crm_lead_line(osv.osv):
    _name = 'crm.lead.line'
    _columns = {
                'lead_id':fields.many2one('crm.lead','Lead'),
                'glass':fields.selection([('Bubble','Bubble'),('Impact SGP','Impact SGP'),('Impact PVB','Impact PVB'),('Aquatex','Aquatex'),('Rain','Rain'),('Frosted','Frosted'),('Low-E Clear','Low-E Clear'),('Clear','Clear (Non-insulated)'),('None','None')],'Glass'),
                'door_to':fields.selection([('Single','Single'),('Double','Double')],'Single Or Double Door'),
                'function_line': fields.selection([('home Owner','home Owner'),('Builder','Builder'),('Architecture','Architecture'),('Designer','Designer'),('Other','Other')],'Function'),
                'remodel':fields.selection([('Remodel','Remodel'),('New Construction','New Construction'),('None','None')],'New Construction or Remodel'),
                'door_width':fields.float('Door Width (inches)',digits=(12,3)),
                'door_height':fields.float('Door Height (inches)',digits=(12,3)),
                'descip':fields.text('Notes'),
                'shape':fields.selection([('Flat Top','Flat Top'),('Eyebrow','Eyebrow'),('Full Arch','Full Arch')],'Shape'),
                'bore':fields.selection([('Double','Double'),('Single','Single')],'Bore'),
                'jamb':fields.selection([('6 inch','6 inch'),('8 inch','8 inch'),('Other','Other')],'Jamb'),
                'new_jamb':fields.char('New Jamb'),
                'impact':fields.selection([('Impact','Impact (hurricane construction)'),('Non-Impact','Non-Impact'),('None','None')],'Impact or Non Impact'),
                'stock_custom':fields.selection([('Custom','Custom'),('Stock','Stock'),('None','None')],'Stock or Custom'),
                'swing':fields.selection([('Right Hand IN SWING','Right Hand IN SWING'),('Right Hand OUT SWING','Right Hand OUT SWING'),('Left Hand IN SWING','Left Hand IN SWING'),('Left Hand OUT SWING','Left Hand OUT SWING')],'Swing'),
                'adoor':fields.selection([('Left Hand Active (standing outside the home)','Left Hand Active (standing outside the home)'),('Right Hand Active (standing outside the home)','Right Hand Active (standing outside the home)'),('None','None')],'Active Door'),
                #'color':fields.selection([('Dark Bronze','Dark Bronze'),('Black','Black'),('Other','Other')],'Color'),
                'color':fields.selection([('Dark Bronze','Dark Bronze'),
                                          ('Light Bronze','Light Bronze'), 
                                          ('Dark Pewter','Dark Pewter'),
                                          ('Light Pewter','Light Pewter'), 
                                          ('Black','Black')],'Color'),
                
                'new_color':fields.char('New Color'),
                'glass':fields.selection([('Low E Clear','Low E Clear'),('Impact SGP','Impact SGP'),('Water Cube','Water Cube'),('Aquatex','Aquatex'),('Rain','Rain'),('Other','Other')],'Glass'),
                'o_glass':fields.boolean('Operable Glass'),
                'inst_mount':fields.selection([('Tabbed','Tabbed'),('Side Mount','Side Mount')],'Install Mount'),
                'trans_arch':fields.selection([('Flat Top','Flat Top'),('Eyebrow','Eyebrow'),('Full Arch','Full Arch')],'Transom Arch'),
                'trans_height':fields.float('Transom Height (inches)'),
                'trans_width':fields.float('Transom Width (inches)'),
                'side_arch':fields.selection([('Flat Top','Flat Top'),('Eyebrow','Eyebrow'),('Full Arch','Full Arch')],'Sidelight Arch'),
                'side_height':fields.float('Sidelight Height (inches)'),
                'side_width':fields.float('Sidelight Width (inches)'),
                'day_visit':fields.date('Days Visited'),
                'no_of_chart':fields.integer('Number of Charts'),
                'f_visit_time':fields.datetime('First Visited Time'),
                'referrer':fields.char('Referrer'),
                'time_spent':fields.datetime('Average Time Spent (minutes)'),
                'lvisit_time':fields.datetime('Last Visited Time'),
                'fvisit_time':fields.char('First Visited URL'),
                'lead_status':fields.selection([('Not Attempted','Not Attempted'),('Attempted','Attempted to Contact'),('Contacted','Contacted'),('junk_lead','Junk Lead'),('Opportunity','New Opportunity'),('Disqualified','Disqualified')],'Lead Status'),
                'lead_source':fields.selection([('Google','Google'),('Bing','Bing'),('Direct Mailer','Direct Mailer'),('Ebay','Ebay'),('Craigslist','Craigslist'),('Saw the truck','Saw the Truck'),('Referral','Referral'),('Trade Show','Trade Show'),('Chat','Chat')],'Lead Source'),            
                'cad_partner_email':fields.char('CAD Draw Email'),
                'mail_msg':fields.text("Mail Message"),
                'attachment_ids': fields.many2many('ir.attachment', 'crm_lead_attachment_rel', 'lead_id',
                                    'attachment_id', 'Attachments'),
                'hdwr':fields.selection([('Pull Handle','Pull Handle'),('Handle Set','Handle Set')],"Hardware"),
               
                'thresold':fields.selection([('Welded Metal','Welded Metal'),('Adjustable','Adjustable'),('Other','Other')],'Thresold'),
                'customer_ref':fields.char("Customer Reference"),
                'door_seq':fields.selection([('DOOR1','Door1'),('DOOR2','Door2')],'Door Sequence'),
                'trans_seq':fields.selection([('TRANSOM1','Transom1'),('TRANSOM2','Transom2')],'Trans Sequence'),
                'side_seq':fields.selection([('SIDELIGHT1','Sidelight1'),('SIDELIGHT2','Sidelight2')],'Sidelight Sequence'),

                }
    
    def onchange_color(self,cr,uid,ids,color,context=None):
        if color != 'Other':
            value = {
                     'new_color':color,
                     }
            return {'value':value}
        value = {
                  'new_color':None,
                 }
        return {'value':value}
    
    def onchange_jamb(self,cr,uid,ids,jamb,context=None):
        if jamb != 'Other':
            value = {
                     'new_jamb':jamb,
                     }
            return {'value':value}
        value = {
                  'new_jamb':None,
                 }
        return {'value':value}
crm_lead_line()
