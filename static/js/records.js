$(document).ready(function () {
  get_records_ini();
});

function formateDateTime(m) {
  var hours = m.getHours();
  var ampm = hours >= 12 ? 'PM' : 'AM';
  hours = hours % 12;
  hours = hours ? hours : 12;

  return m.getFullYear() + "-" +
    ("0" + (m.getMonth() + 1)).slice(-2) + "-" +
    ("0" + m.getDate()).slice(-2) + " " +
    hours + ":" +
    ("0" + m.getMinutes()).slice(-2) + ":" +
    ("0" + m.getSeconds()).slice(-2) + ' ' +
    ampm;
}

function getRecords(page) {
  page_size = 4;
  $.get("/records", {
    page: page,
    page_size: page_size
  }, function (data) {
    if (data && data.results) {
      var tbl_body = "";
      data.results.forEach(record => {
        var tbl_row = "";
        tbl_row += "<td class='sub-title'>" + (record.p_timestamp ? formateDateTime(new Date(record.p_timestamp)) : '') + "</td>";
        tbl_row += "<td class='sub-title'>" + (record.p_identification ? record.p_identification : '') + "</td>";
        tbl_row += "<td class='sub-title'>" + (record.p_name ? record.p_name : '') + "</td>";
        tbl_row += "<td class='sub-title'>" + (record.p_last_name ? record.p_last_name : '') + "</td>";
        tbl_row += "<td class='sub-title'>" + (record.t_temperature_body ? record.t_temperature_body : '') + "</td>";

        alert_html = ""
        if (record.t_alert == 0) {
          alert_html = "<button type='button' class='btn btn-success alert_button_records'>Permitido</button>";
        } else if (record.t_alert == 1) {
          alert_html = "<button type='button' class='btn btn-warning alert_button_records'>Advertencia</button>";
        } else if (record.t_alert == 2) {
          alert_html = "<button type='button' class='btn btn-danger alert_button_records'>Peligro</button>";
        }
        tbl_row += "<td class='sub-title'>" + alert_html + "</td>";
        tbl_row += "<td>" + (record.t_image_thermal ? "<img src='data:image/png;base64, " + record.t_image_thermal + "' width=200>" : '') + "</td>";
        tbl_row += "<td>" + (record.t_image_rgb ? "<img src='data:image/png;base64, " + record.t_image_rgb + "' width=200>" : '') + "</td>";
        tbl_body += "<tr>" + tbl_row + "</tr>";
      });

      $("#table-register").html(tbl_body);

      var pagination_body = "";
      number_pages = Math.ceil(data.count / page_size);
      pagination_body += '<li class="page-item"><a class="page-link" href="javascript:void(0)" onclick="getRecords(' + 1 + ');">Primera</a></li>';

      var radius = 3;
      var max_min = number_pages - 2 * radius;
      var min = (page - radius) > 0 ? ((page - radius) <= max_min ? (page - radius) : max_min) : 1;
      var max = (min + 2 * radius) <= number_pages ? (min + 2 * radius) : number_pages;
      for (i = min; i <= max; i++) {
        pagination_body += '<li class="page-item' + (page == i ? ' active' : '') + '"><a class="page-link test" href="javascript:void(0)" onclick="getRecords(' + i + ');">' + i + '</a></li>';
      }
      pagination_body += '<li class="page-item"><a class="page-link" href="javascript:void(0)" onclick="getRecords(' + number_pages + ');">Última</a></li>';

      $("#records_pagination").html(pagination_body);
    }
  });
}

//cfernandez - 10/10/2020
function get_records_ini(){
  $('#table_records').DataTable({
    bProcessing: true,
    bServerSide: true,
    sPaginationType: "full_numbers",
    lengthMenu: [[10, 25, 50, 100], [10, 25, 50, 100]],
    bjQueryUI: true,
    sAjaxSource: '/serverside_table',
    columns: [{"data": "data1"},
      {"data": "data2"},
      {"data": "data3"},
      {"data": "data4"},
      {"data": "data5"},
      {"data": "data6"},
      /*{"data": "data6",
        "render": function (data) {
          if (data == 0) {
            x = '<span class="badge badge-success">Permitido</span>';
          } else if (data == 1) {
            x = '<span class="badge badge-warning">Advertencia</span>';
          } else if (data == 2) {
            x = '<span class="badge badge-danger">Peligro</span>';
          }
          return x;
        }},*/
      {"data": "data7",
        "render": function (data) {
          return '<img src="data:image/jpeg;base64,' + data + '" height="100px" />';
        }},
      {"data": "data8",
        "render": function (data) {
          return '<img src="data:image/jpeg;base64,' + data + '" height="100px" />';
        }}
    ]
  });
}

//cfernandez - 10/10/2020
function records_search() {
  f_ingreso = $("#f_ingreso").val();

  if (f_ingreso == 0) {
    aux = 'Permitido';
  } else if (f_ingreso == 1) {
    aux = 'Advertencia';
  } else if (f_ingreso == 2) {
    aux = 'Peligro';
  } else if (f_ingreso == 3) {
    aux = '';
  }

  var table = $('#table_records').DataTable();

  table.search(aux).draw();
}

//cfernandez - 10/10/2020
function download_csv() {
  f_ingreso = $("#f_ingreso").val();

  url = '/records_csv?f_ingreso=' + f_ingreso

  window.open(
    url,
    '_blank' // <- This is what makes it open in a new window.
  );
}

