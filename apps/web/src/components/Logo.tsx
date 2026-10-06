import logo from "../assets/images/logo.png";

function Logo() {
  return (
    <div className="shrink-0">
      <img
        src={logo}
        alt="FashionOS"
        className="
          block
          w-12 h-12
          sm:w-14 sm:h-14
          md:w-16 md:h-16
          lg:w-18 lg:h-18
          xl:w-20 xl:h-20
          object-contain
          m-2
        "
      />
    </div>
  );
}

export default Logo;
