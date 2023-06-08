<h1 align='center'>Paddle Club administration</h1>
  <h3 align='center'>Web service for a Paddle club administration</h3>
   <p align="center">
    <img src="https://img.shields.io/badge/STATUS-DEVELOPING-green">
   </p>
   <p align="center">
    <a href="#spain"><img src="https://img.freepik.com/iconos-gratis/espana_318-203514.jpg" width="36" height="36"></a>
    <a href="#uk"><img src="https://cdn-icons-png.flaticon.com/512/323/323329.png?w=826&t=st=1683064095~exp=1683064695~hmac=596022b81fb1d26046ffa17161f4aa65c80712f1e31848c69da8984c322b9295" width="36" height="36"></a>
   </p>
   
  <h2 id="spain">Descripción</h2>
  <p>
Un emprendedor quiere fundar su propio club de pádel en las afueras de Vilanova y la Geltrú.
Para poder gestionar el club de manera correcta necesitan una base de datos con determinadas necesidades.
El club estará abierto de lunes a domingo, de 9 a 21.

El club de pádel estará formado por jugadores. Los jugadores estarán identificados por un id. También queremos saber su nombre, apellido, nivel de juego, número de teléfono, dirección de correo electrónico y contraseña. El nivel de juego será un número entre 1 y 6 que indicará como de bien juegan (cuánto más alto mejor jugador).
Los jugadores juegan a pádel a las pistas de pádel. Como que no tendremos un gran número de pistas, estas estarán identificadas por un número (Pista 1, Pista 2, Pista 3...). Las pistas pueden ser del tipo Outdoor o Indoor. En una misma pista pueden jugar mínimo 2 jugadores y máximo 4.

Para que los jugadores puedan jugar a la pista, al menos uno habrá tenido que hacer una reserva previamente. Para cada reserva, hay que registrar la fecha, la hora de inicio de la reserva y la hora de finalización. La reserva se identificará dado una fecha y el jugador que ha hecho la reserva. Las horas de reserva disponibles son cada media hora, es decir, de 9:00-9:30,10:00... así hasta las 21:00. Una reserva tiene una duración mínima de 30 minutos y máxima de 1 hora y 30 minutos.

Por cada reserva también tendremos que saber la pista reservada y los jugadores que participan en el juego. Un jugador solo podrá hacer una reserva por día, y no podrá estar asignado a dos reservas a la vegada si estas dos coinciden en horas.

Antes de entrar a pista para jugar, cada jugador asociado a la reserva de la pista habrá tenido que hacer un pago, que para el club será un cobro. Un cobro contendrá la fecha del cobro, importe abonado y el jugador que ha efectuado el cobro por la reserva.

Para disfrutar de ciertas ventajas, los jugadores pueden hacerse socios del club. Ser miembro del club costará 35 euros en el mes, pago que se efectuará mediante un cargo a un IBAN.

Los socios podrán jugar gratis en las pistas de 9.00 a 13.00 de lunes a viernes y tendrán un descuento del 50% en las otras horas.

Para hacerse socio se tendrá que indicar un número de cuenta bancario (IBAN).

El cobro de socio estará identificado por un íd, y se hará efectivo el último día de cada mes, fecha que se guardará a la base de datos.

Al club de pádel tendremos unos recepcionistas. Estas personas tendrán acceso total a la base de datos. Podrán añadir/eliminar jugadores a las reservas, crear reservas y serán las únicas personas que podrán eliminar reservas (junto con el jugador creador de la reserva). También se encargarán de realizar los cobros de los jugadores antes de entrar a jugar a la pista. A pesar de que todos tienen acceso total, a la base de datos solo guardaremos el/la recepcionista que ha gestionado la reserva y qué recepcionista ha realizado el cobro. El recepcionistas se identificarán con su DNI y también querremos saber su nombre, apellido, email, contraseña y un teléfono.

  </p>
  <br>
<h2 id="uk">Description</h2>
<p>
An entrepreneur wants to found his own paddle tennis club on the outskirts of Vilanova y la Geltrú.

To be able to manage the club correctly, they need a database with certain needs.
The club will be open from Monday to Sunday, from 9 to 21.

The paddle club will consist of players. Players will be identified by an id. We also want to know his name, surname, game level, phone number, email address and password. The game level will be a number between 1 and 6 indicating how well they play (how much higher the player is).
Players play paddle on the paddle courts. Since we will not have a large number of ourts, these will be identified by a number (court 1, court 2, court 3...). The courts may be of the Outdoor or Indoor type. At least 2 players and maximum 4 can play on the same court.

In order for players to play on the court, at least one has had to make a reservation. For each reservation, the date, start time of the reservation and end time must be recorded. The reserve will be identified by a date and the player who made the reserve. The available reserve hours are every half hour, i.e. 9:00-9:30.10:00... So until 9 p.m. A reservation has a minimum duration of 30 minutes and a maximum of 1 hour and 30 minutes.

For each reserve we will also need to know the reserved court and the players involved in the game. A player will only be able to book one reserve per day, and will not be assigned to two reserves at once if these two match in hours.

Before entering the court to play, each player associated with the reserve of the track has had to make a payment, which for the club will be a fee. A charge will contain the date of the charge, amount paid and the player who has made the recovery by the reserve.

To enjoy certain advantages, players can become members of the club. A member of the club will cost EUR 35 per month, payment that will be made through an IBAN charge.

Members will be able to play free on tracks from 9 a.m. to 13 a.m. from Monday to Friday and will have a 50% discount in the other hours.

To become a member, a bank account number (IBAN) must be specified.

Membership collection will be identified by an ID, and will be effective on the last day of each month, the date that will be stored in the database.

At the paddle club we'll have some recepcionists. These people will have full access to the database. They will be able to add/remove players to the reserves, create reserves and be the only people who will be able to remove reserves (along with the player who created the reserve). They will also charge for collecting players before entering the court. Although everyone has full access, we will only save the receptionist who managed the reserve and which receptionist made the recovery in the database. Recepcionists will identify with their DNI and we will also want to know their name, surname, email, password and phone.
</p>
  
  <br>
  <h2>UML</h2>
  <p align="center">
    <img src="https://github.com/raulgamero/paddle-club-administration/blob/master/uml.png"></img>
    <ul>
      <li>RS1 - Entre la hora de inicio y finalización de una reserva hay un intervalo de mínimo 30 minutos y máximo 1 hora 30 minutos</li>
      <li>RS2 - Dada una reserva r1 asociada a una pista p1, no puede exisitr otra reserva r2 también asociada a p1 que contenga r1.hora_inicio <= r2.hora_inicio <= r1.hora_finalización o r1.hora_inicio <= r2.hora_finalización <= r1.hora_finalización</li>
      <li>RS3 - Dado un jugador j1, una reserva r1 asociada a una pista p1 y una reserva r2 asociada a p2, j1 no podra estar asociado a r2 si ya está asociado a r1 y r1.hora_inicio <= r2.hora_inicio <= r1.hora_finalización o r1.hora_inicio <= r2.hora_finalización <= r1.hora_finalización</li>
      <li>RS4 - Dado un jugador j1 que ha realizado una reserva r1 (quiReserva) tendrá que existir un cobro(j1, r1).</li>
    </ul>
  </p>
  <br>
  <h2>Tech Stack</h2>
  <p>
    <a href="https://www.djangoproject.com/" target="_blank"><img src="https://brandslogos.com/wp-content/uploads/images/large/django-logo.png" width="40" height="50" alt="Django" /></a>
    <a href="https://www.postgresql.org/" target="_blank"><img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/postgresql/postgresql-original.svg" width="50" height="50" alt="PostgreSQL" /></a>
    <a href="https://en.wikipedia.org/wiki/JavaScript" target="_blank" rel="noreferrer"><img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/javascript/javascript-original.svg" width="50" height="50" alt="JavaScript" /></a>
    <a href="https://developer.mozilla.org/en-US/docs/Glossary/HTML5" target="_blank" rel="noreferrer"><img src="https://raw.githubusercontent.com/danielcranney/readme-generator/main/public/icons/skills/html5-colored.svg" width="50" height="50" alt="HTML5" /></a>
    <a href="https://www.w3.org/TR/CSS/#css" target="_blank" rel="noreferrer"><img src="https://raw.githubusercontent.com/danielcranney/readme-generator/main/public/icons/skills/css3-colored.svg" width="50" height="50" alt="CSS3" /></a>
  <img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/tailwindcss/tailwindcss-plain.svg" width="50" height="50" alt="Tailwind" /
  </p>
