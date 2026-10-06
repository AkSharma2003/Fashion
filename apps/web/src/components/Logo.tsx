import logo from "../assets/images/logo.png";

function Logo() {
  console.log("LOGO:", logo);

  return (
    <div>
      <img
        className="mx-auto block h-15 sm:mx-0 sm:shrink-0 "
        src={logo}
        alt="FashionOS"
      />
    </div>
  );
}

export default Logo;