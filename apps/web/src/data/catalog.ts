import type { ClothingCardProduct } from "../components/Card";

export const sareeProducts: ClothingCardProduct[] = [
  {
    name: "Sunehri Silk Saree",
    description: "A festive silk saree with a rich woven border, made for celebrations and special evenings.",
    price: 2499,
    image: "https://images.unsplash.com/photo-1610030469983-98e550d6193c?auto=format&fit=crop&w=900&q=85",
    imageAlt: "Model wearing a red silk saree with a detailed border",
    colors: [{ name: "Ruby red", value: "#9E2638" }, { name: "Antique gold", value: "#C6A15B" }, { name: "Deep green", value: "#315B48" }],
    tag: "Bestseller",
  },
  {
    name: "Sunlit Mustard Saree",
    description: "A bright traditional drape with delicate gold motifs and a graceful festive finish.",
    price: 2199,
    image: "https://images.unsplash.com/photo-1609748341642-ae4c6562bf3d?auto=format&fit=crop&w=900&q=85",
    imageAlt: "Model wearing a mustard yellow saree with gold motifs",
    colors: [{ name: "Mustard", value: "#D7A928" }, { name: "Maroon", value: "#762C3A" }],
    tag: "Festive edit",
  },
  {
    name: "Royal Blue Banarasi Saree",
    description: "A richly colored saree with a contrasting border for weddings and special occasions.",
    price: 3299,
    image: "https://images.unsplash.com/photo-1610189012906-4c0aa9b9781e?auto=format&fit=crop&w=900&q=85",
    imageAlt: "Model wearing a blue saree with a contrasting embroidered border",
    colors: [{ name: "Royal blue", value: "#243D73" }, { name: "Pink", value: "#CF7890" }],
  },
  {
    name: "Floral Blue Saree",
    description: "A statement floral drape that pairs traditional detailing with a lively modern palette.",
    price: 2799,
    image: "https://images.unsplash.com/photo-1610030469978-6bb537f3b982?auto=format&fit=crop&w=900&q=85",
    imageAlt: "Model wearing a blue floral saree",
    colors: [{ name: "Ocean blue", value: "#28528B" }, { name: "Red", value: "#A92739" }],
  },
];

export const suitProducts: ClothingCardProduct[] = [
  {
    name: "Ivory Anarkali Set",
    description: "An elegant flared suit set with fine embroidery and a light dupatta for occasion wear.",
    price: 1899,
    image: "https://www.shauryasanadhya.com/cdn/shop/products/DSC3802.jpg?v=1745482303",
    imageAlt: "Model wearing an ivory embroidered Anarkali suit",
    colors: [{ name: "Ivory", value: "#F1E9D8" }, { name: "Blush pink", value: "#DFA9B5" }],
    tag: "Bestseller",
  },
  {
    name: "Sunshine Anarkali Suit",
    description: "A flowing yellow Anarkali with embroidered accents for a bright celebration look.",
    price: 2299,
    image: "https://variyav.com/cdn/shop/files/20101c_1200x.jpg?v=1727093614",
    imageAlt: "Model wearing a yellow embroidered Anarkali suit",
    colors: [{ name: "Sunshine yellow", value: "#E5B72D" }, { name: "Ivory", value: "#F1E9D8" }],
    tag: "New arrival",
  },
  {
    name: "Crimson Cotton Suit",
    description: "A printed cotton kurta set with a matching dupatta for comfortable all-day wear.",
    price: 1599,
    image: "https://kavyastyleplus.com/cdn/shop/files/Anarkali_20Vol_202_20Balaji_20Readymade_20Suits_20_288_29.jpg?v=1749879081&width=900",
    imageAlt: "Model wearing a red and black printed Anarkali cotton suit",
    colors: [{ name: "Crimson", value: "#A5293E" }, { name: "Black", value: "#242424" }],
  },
  {
    name: "Teal Embroidered Suit",
    description: "A graceful teal ensemble with detailed embroidery and a coordinated dupatta.",
    price: 2899,
    image: "https://kavyastyleplus.com/cdn/shop/products/Vol_2021_20Anjubaa_20Anarkali_20Salwar_20Suits_20_283_29.jpg?v=1703566958&width=900",
    imageAlt: "Model wearing a teal Anarkali suit with silver embroidery",
    colors: [{ name: "Teal", value: "#247A78" }, { name: "Silver", value: "#B9B9B9" }],
  },
];

export const kidsProducts: ClothingCardProduct[] = [
  {
    name: "Little Festive Kurta",
    description: "A comfortable printed kurta set with soft fabric and cheerful colors for family occasions.",
    price: 1299,
    image: "https://scrollandshops.com/cdn/shop/files/Floral_Jaal_Print_Siblings_Set_SNS13297_5_339e5d4b-c029-42b4-a8d9-467b0d843c8e.jpg?v=1755518770",
    imageAlt: "Children wearing coordinated green floral kurta sets",
    colors: [{ name: "Leaf green", value: "#557855" }, { name: "Cream", value: "#EADFC9" }],
    tag: "Bestseller",
  },
  {
    name: "Blue Celebration Set",
    description: "A soft cotton sibling set with playful prints, made for festive family moments.",
    price: 1499,
    image: "https://www.bownbee.com/cdn/shop/files/SLSBN24DK09BB24SU12BLA3.webp?v=1770352821",
    imageAlt: "Children wearing coordinated blue festive ethnic outfits",
    colors: [{ name: "Sky blue", value: "#5793C4" }, { name: "Navy", value: "#253B65" }],
    tag: "Festive edit",
  },
  {
    name: "Mustard Floral Kurta Set",
    description: "A bright cotton kurta set with floral accents and an easy fit for all-day comfort.",
    price: 1199,
    image: "https://aarikascloset.com/cdn/shop/files/siblingset-2_bd081c36-e4a8-4eeb-9fe5-172cae037af0_1400x.jpg?v=1749582004",
    imageAlt: "Children wearing coordinated mustard floral ethnic outfits",
    colors: [{ name: "Mustard", value: "#D5A52B" }, { name: "Leaf green", value: "#557855" }],
  },
  {
    name: "Blue Floral Kurta Set",
    description: "A cheerful floral kurta and sharara set in breathable cotton for little celebrations.",
    price: 1399,
    image: "https://chottuchottifashions.com/cdn/shop/files/Blue-floral-Ethnic-wear-instagram-post-size1-1.png?v=1758554713",
    imageAlt: "Children wearing matching blue floral ethnic outfits",
    colors: [{ name: "Blue", value: "#3E6EAA" }, { name: "White", value: "#F4F1E9" }],
  },
];
