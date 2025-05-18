/** @type {import('next').NextConfig} */
const nextConfig = {

    // Это позволит избежать проблем с загрузкой изображений в Docker
    images: {
      unoptimized: true,
    },
  
    // Отключаем проверку типов при сборке
    typescript: {
      ignoreBuildErrors: true,
    },
};

module.exports = nextConfig; 