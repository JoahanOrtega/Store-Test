import { test, expect } from '@playwright/test';

test('search click', async ({ page }) => {
  test.setTimeout(120000); 
  await page.goto('https://best.aliexpress.com/');
  await expect(page).toHaveTitle(/AliExpress - Compras en línea para productos electrónicos populares, moda, hogar y jardín, juguetes y deportes, automóviles y más./);

  //test 1 "Al ingresar un correo no existente te manda a registrarte"
  await page.locator('img[src="https://img.alicdn.com/tfs/TB1a.Oge_M11u4jSZPxXXahcXXa-48-48.png"]').click();
  await page.locator('img[src="https://img.alicdn.com/tfs/TB1GSux3fb2gK0jSZK9XXaEgFXa-21-21.png"]').click();

  await page.locator('div[class="lgh-contain-login-btn ellipsis"]:has-text("Sign in")').click();
  await page.locator('span[class="cosmos-input-label-content"]').click();
  await page.locator('input[class="cosmos-input cosmos-input-focused"]').fill('examplemailnoexist@gmail.com');
  await page.locator('img[src="https://ae01.alicdn.com/kf/S162b092c979744b9a75d8986c7168c79F/804x52.png"]').click();
  await page.locator('button:has-text("Continuar")').click({ delay: 4000 });
  await page.locator('img[src="https://ae01.alicdn.com/kf/S01bcb83288924ee68a2087ef084c0d9dW/48x48.png"]').click();
  //await page.locator('a[class="cJuIY"]').click();
  
  //test 2 "Al ingresar un correo existente y contraseña correcta inicia sesión correctamente"
  await page.locator('div[class="lgh-contain-login-btn ellipsis"]:has-text("Sign in")').click({delay:3000});
  await page.locator('span[class="cosmos-input-label-content"]').click();
  await page.locator('input[class="cosmos-input cosmos-input-focused"]').fill('cristianprimeprueba24@gmail.com');
  await page.locator('img[src="https://ae01.alicdn.com/kf/S162b092c979744b9a75d8986c7168c79F/804x52.png"]').click();
  await page.locator('button:has-text("Continuar")').click({ delay: 4000 });
  await page.locator('span[class="cosmos-input-label-wrapper cosmos-input-password _3fgZ7"]').click();
  await page.locator('input[id="fm-login-password"]').fill('Prueba123');
  await page.locator('button:has-text("Iniciar Sesión")').click({ delay: 4000 });

  const frame = await page.frameLocator('#baxia-dialog-content');
  const slider = frame.locator('span.btn_slide');
  await slider.waitFor({ state: 'visible', timeout: 10000 });
  const sliderBox = await slider.boundingBox();
  if (sliderBox) {
    await page.mouse.move(sliderBox.x + sliderBox.width / 2, sliderBox.y + sliderBox.height / 2); // Punto de inicio
    await page.mouse.down(); // Presionar clic
    await page.mouse.move(sliderBox.x + sliderBox.width + 300, sliderBox.y + sliderBox.height / 2, { steps: 50 }); // Deslizar hacia la derecha
    await page.mouse.up(); // Soltar clic
  }
  await page.locator('img[src="https://ae01.alicdn.com/kf/S01bcb83288924ee68a2087ef084c0d9dW/48x48.png"]').click();
  await page.locator('a[class="cJuIY"]').click(); 

  //test 3 "Busqueda de un producto en especifico, filtrar por "envio gratis" y seleccionar un producto en especifico"
  const searchInput = page.locator('input[class="search--keyword--15P08Ji"]');
  await expect(searchInput).toBeVisible();
  await searchInput.fill("airpods");
  await page.waitForTimeout(3000);
  await page.keyboard.press('Enter');
  await page.getByText('Entrega en 15 días').click({delay:3000});

  const page1Promise = page.waitForEvent('popup');
  await page.getByRole('link', { name: 'Report fraud item Apple AirPods 4 cancelación activa de ruido potente chip H2' }).click();
  const page1 = await page1Promise;
  await page1.locator('._24EHh').click();
  await page1.locator('[id="_full_container_header_23_"]').getByRole('link', { name: 'AliExpress' }).click();

  //test 4 "Se regreso al inicio y ahora se buscará un producto en especifico mediante el apartado de categorias "
  await page1.locator('div[class="Categoey--controlCategory--3xX8k7k"]').hover();
  await page1.locator('li[data="consumer_electronics"]').click({delay:2000});
  await page1.locator('[id="_full_container_header_23_"] img').nth(3).click();
  await page1.getByRole('link', { name: 'Consolas', exact: true }).click({delay:3000});
  const page2Promise = page1.waitForEvent('popup');
  await page1.getByRole('link', { name: 'Report fraud item Consola de videojuegos portátil Retro R36S, sistema Linux,' }).click({delay:3000});
  const page2 = await page2Promise;
  //await page2.locator('._24EHh').click();
  await page2.locator('[id="_full_container_header_23_"]').getByRole('link', { name: 'AliExpress' }).click();

  //test 5 "Se regreso al inicio y por utlimo se va a cambiar el pais de envio, el idioma y la moneda"
  await page2.locator('span[class="ship-to--cssFlag--3qFf5C9 country-flag-y2023 MX"]').click({delay:3000});
  await page2.locator('.select--text--1b85oDo').first().click({ delay: 2000 });
  await page2.locator('div:nth-child(59)').click({delay:2000});
  await page2.locator('div:nth-child(4) > .select--wrap--3N7DHe_ > .select--text--1b85oDo > .select--arrow--1cha40Y').click({ delay: 2000 });
  await page2.locator('[id="_full_container_header_23_"]').getByText('Español').click({ delay: 2000 });
  await page2.locator('div:nth-child(6) > .select--wrap--3N7DHe_ > .select--text--1b85oDo > .select--arrow--1cha40Y').click({ delay: 2000 });
  await page2.getByText('USD ( Dólar estadounidense )').click({ delay: 2000 });
  await page2.locator('[id="_full_container_header_23_"]').getByText('Guardar').click({ delay: 2000 });

  await page2.pause()
})